from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.reservation import Reservation, ReservationStatus
from app.models.studio import Subscription, TimeSlot
from app.models.user import User, UserRole
from app.services import google_calendar as gcal
from app.services import subscriptions as sub_service


def _serialize(reservation: Reservation) -> dict:
    return {
        "id": reservation.id,
        "user_id": reservation.user_id,
        "studio_id": reservation.studio_id,
        "time_slot_id": reservation.time_slot_id,
        "status": reservation.status,
        "note": reservation.note,
        "google_event_id": reservation.google_event_id,
        "created_at": reservation.created_at,
        "cancelled_at": reservation.cancelled_at,
        "studio_name": reservation.studio.name if reservation.studio else None,
        "user_name": reservation.user.full_name if reservation.user else None,
        "user_email": reservation.user.email if reservation.user else None,
        "start_at": reservation.time_slot.start_at if reservation.time_slot else None,
        "end_at": reservation.time_slot.end_at if reservation.time_slot else None,
    }


def list_reservations(
    db: Session,
    current_user: User,
    *,
    q: str | None = None,
    studio_id: int | None = None,
    status_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[dict]:
    stmt = (
        select(Reservation)
        .options(
            joinedload(Reservation.studio),
            joinedload(Reservation.user),
            joinedload(Reservation.time_slot),
        )
        .join(TimeSlot, Reservation.time_slot_id == TimeSlot.id)
        .join(User, Reservation.user_id == User.id)
    )

    if current_user.role != UserRole.ADMIN.value:
        stmt = stmt.where(Reservation.user_id == current_user.id)

    if studio_id:
        stmt = stmt.where(Reservation.studio_id == studio_id)
    if status_filter:
        stmt = stmt.where(Reservation.status == status_filter)
    if date_from:
        stmt = stmt.where(TimeSlot.start_at >= date_from)
    if date_to:
        stmt = stmt.where(TimeSlot.start_at <= date_to)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Reservation.note.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )

    stmt = stmt.order_by(TimeSlot.start_at.desc()).offset(skip).limit(limit)
    rows = db.scalars(stmt).unique().all()
    return [_serialize(r) for r in rows]


def get_reservation(db: Session, reservation_id: int, current_user: User) -> dict:
    reservation = db.scalars(
        select(Reservation)
        .options(
            joinedload(Reservation.studio),
            joinedload(Reservation.user),
            joinedload(Reservation.time_slot),
        )
        .where(Reservation.id == reservation_id)
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="予約が見つかりません")
    if current_user.role != UserRole.ADMIN.value and reservation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="この予約を閲覧する権限がありません")
    return _serialize(reservation)


def create_reservation(db: Session, current_user: User, time_slot_id: int, note: str | None) -> dict:
    slot = db.scalars(
        select(TimeSlot).options(joinedload(TimeSlot.studio)).where(TimeSlot.id == time_slot_id)
    ).first()
    if not slot or not slot.is_available:
        raise HTTPException(status_code=400, detail="指定の枠は予約できません")
    if gcal.ensure_aware(slot.start_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="過去の枠は予約できません")

    sub = sub_service.require_bookable_subscription(db, current_user.id)

    reservation = Reservation(
        user_id=current_user.id,
        studio_id=slot.studio_id,
        time_slot_id=slot.id,
        status=ReservationStatus.CONFIRMED.value,
        note=note,
    )
    slot.is_available = False
    sub.used_count += 1
    db.add(reservation)
    db.add(slot)
    db.add(sub)
    db.commit()
    db.refresh(reservation)

    reservation = db.scalars(
        select(Reservation)
        .options(
            joinedload(Reservation.studio),
            joinedload(Reservation.user),
            joinedload(Reservation.time_slot),
        )
        .where(Reservation.id == reservation.id)
    ).first()

    try:
        event_id = gcal.create_calendar_event(current_user, reservation)
        if event_id:
            reservation.google_event_id = event_id
            db.add(reservation)
            db.commit()
            db.refresh(reservation)
    except Exception:
        # カレンダー失敗でも予約自体は成功扱いにする
        pass

    return _serialize(reservation)


def cancel_reservation(db: Session, reservation_id: int, current_user: User) -> dict:
    reservation = db.scalars(
        select(Reservation)
        .options(
            joinedload(Reservation.studio),
            joinedload(Reservation.user),
            joinedload(Reservation.time_slot),
        )
        .where(Reservation.id == reservation_id)
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="予約が見つかりません")

    is_admin = current_user.role == UserRole.ADMIN.value
    if not is_admin and reservation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="この予約をキャンセルする権限がありません")
    if reservation.status == ReservationStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="既にキャンセル済みです")

    if not gcal.can_cancel(
        reservation.time_slot.start_at,
        is_admin=is_admin,
        hours_before=settings.cancel_hours_before,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"開始 {settings.cancel_hours_before} 時間前を過ぎているためキャンセルできません",
        )

    try:
        gcal.delete_calendar_event(reservation.user, reservation.google_event_id)
    except Exception:
        pass

    reservation.status = ReservationStatus.CANCELLED.value
    reservation.cancelled_at = datetime.now(timezone.utc)
    reservation.time_slot.is_available = True

    sub = db.scalars(select(Subscription).where(Subscription.user_id == reservation.user_id)).first()
    if sub and sub.used_count > 0:
        sub.used_count -= 1
        db.add(sub)

    db.add(reservation)
    db.add(reservation.time_slot)
    db.commit()
    db.refresh(reservation)
    return _serialize(reservation)


def search_available_slots(
    db: Session,
    *,
    studio_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(TimeSlot)
        .options(joinedload(TimeSlot.studio))
        .where(and_(TimeSlot.is_available.is_(True), TimeSlot.start_at >= now))
    )
    if studio_id:
        stmt = stmt.where(TimeSlot.studio_id == studio_id)
    if date_from:
        stmt = stmt.where(TimeSlot.start_at >= date_from)
    if date_to:
        stmt = stmt.where(TimeSlot.start_at <= date_to)

    slots = db.scalars(stmt.order_by(TimeSlot.start_at.asc()).limit(200)).unique().all()
    return [
        {
            "id": s.id,
            "studio_id": s.studio_id,
            "start_at": s.start_at,
            "end_at": s.end_at,
            "is_available": s.is_available,
            "studio_name": s.studio.name if s.studio else None,
        }
        for s in slots
    ]
