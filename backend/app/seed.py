"""初期・デモデータ投入。不足分のみ追加（再実行しても安全）。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    EmailNotification,
    Invoice,
    InvoiceStatus,
    Reservation,
    ReservationStatus,
    Studio,
    Subscription,
    TimeSlot,
    User,
    UserRole,
)
from app.services import subscriptions as sub_service

SAMPLE_NOTE = "[sample]"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_users(db) -> tuple[User, User, User]:
    admin = db.scalars(select(User).where(User.email == "admin@studio.local")).first()
    if not admin:
        admin = User(
            email="admin@studio.local",
            hashed_password=hash_password("admin1234"),
            full_name="Studio Admin",
            role=UserRole.ADMIN.value,
        )
        db.add(admin)

    member = db.scalars(select(User).where(User.email == "member@studio.local")).first()
    if not member:
        member = User(
            email="member@studio.local",
            hashed_password=hash_password("member1234"),
            full_name="Demo Member",
            role=UserRole.MEMBER.value,
        )
        db.add(member)

    member2 = db.scalars(select(User).where(User.email == "member2@studio.local")).first()
    if not member2:
        member2 = User(
            email="member2@studio.local",
            hashed_password=hash_password("member1234"),
            full_name="Demo Member 2",
            role=UserRole.MEMBER.value,
        )
        db.add(member2)

    db.flush()
    return admin, member, member2


def _ensure_subscription(db, user: User, plan, *, force_plan: bool = False) -> Subscription:
    sub = db.scalars(select(Subscription).where(Subscription.user_id == user.id)).first()
    now = _utcnow()
    if not sub:
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id if plan else None,
            plan_name=plan.name if plan else "Standard",
            monthly_quota=plan.monthly_quota if plan else 8,
            used_count=0,
            period_start=now,
            period_end=now + timedelta(days=30),
            status="active",
            auto_renew=True,
            is_active=True,
        )
        db.add(sub)
        db.flush()
        return sub

    if plan and (force_plan or sub.plan_id is None):
        sub.plan_id = plan.id
        sub.plan_name = plan.name
        sub.monthly_quota = plan.monthly_quota
    if not sub.status:
        sub.status = "active"
    sub.is_active = True
    if sub.period_end < now:
        sub.period_start = now
        sub.period_end = now + timedelta(days=30)
    db.add(sub)
    db.flush()
    return sub


def _ensure_studios_and_slots(db) -> list[Studio]:
    defs = [
        ("Studio A — 白ホリ", "白ホリゾント。ポートレート向け。", 1),
        ("Studio B — 黒背景", "黒背景・機材充実。", 1),
        ("Studio C — 自然光", "大きな窓のある自然光スタジオ。", 2),
    ]
    studios: list[Studio] = []
    for name, desc, capacity in defs:
        studio = db.scalars(select(Studio).where(Studio.name == name)).first()
        if not studio:
            studio = Studio(name=name, description=desc, capacity=capacity, is_active=True)
            db.add(studio)
            db.flush()
        studios.append(studio)

    now = _utcnow()
    for studio in studios:
        existing = db.scalars(select(TimeSlot).where(TimeSlot.studio_id == studio.id).limit(1)).first()
        if existing:
            continue
        slots: list[TimeSlot] = []
        for day in range(1, 21):
            day_base = (now + timedelta(days=day)).replace(hour=0, minute=0, second=0, microsecond=0)
            for hour, end in ((10, 13), (14, 17), (18, 21)):
                slots.append(
                    TimeSlot(
                        studio_id=studio.id,
                        start_at=day_base.replace(hour=hour),
                        end_at=day_base.replace(hour=end),
                        is_available=True,
                    )
                )
        db.add_all(slots)
    db.flush()
    return studios


def _pick_free_slot(db, studio_id: int | None = None, offset: int = 0) -> TimeSlot | None:
    q = (
        select(TimeSlot)
        .where(TimeSlot.is_available.is_(True), TimeSlot.start_at > _utcnow())
        .order_by(TimeSlot.start_at.asc())
    )
    if studio_id is not None:
        q = q.where(TimeSlot.studio_id == studio_id)
    slots = db.scalars(q).all()
    if not slots:
        return None
    return slots[min(offset, len(slots) - 1)]


def _ensure_reservation(
    db,
    *,
    user: User,
    studio: Studio,
    note: str,
    status: str = ReservationStatus.CONFIRMED.value,
    slot_offset: int = 0,
) -> Reservation | None:
    existing = db.scalars(
        select(Reservation).where(
            Reservation.user_id == user.id,
            Reservation.note == note,
        )
    ).first()
    if existing:
        return existing

    slot = _pick_free_slot(db, studio.id, offset=slot_offset)
    if not slot:
        return None

    reservation = Reservation(
        user_id=user.id,
        studio_id=studio.id,
        time_slot_id=slot.id,
        status=status,
        note=note,
    )
    if status == ReservationStatus.CANCELLED.value:
        reservation.cancelled_at = _utcnow()
        slot.is_available = True
    else:
        slot.is_available = False

    db.add(reservation)
    db.add(slot)
    db.flush()
    return reservation


def _ensure_invoices(db, user: User, sub: Subscription, plan) -> None:
    existing = db.scalars(select(Invoice).where(Invoice.user_id == user.id).limit(1)).first()
    if existing:
        return

    now = _utcnow()
    price = plan.price_yen if plan else 19800
    tax = int(price * 0.1)
    total = price + tax
    lines = json.dumps(
        [{"description": f"{plan.name if plan else 'Plan'} 月額", "amount_yen": price}],
        ensure_ascii=False,
    )
    invoices = [
        Invoice(
            user_id=user.id,
            subscription_id=sub.id,
            number=f"INV-{now.strftime('%Y%m%d')}-S001",
            status=InvoiceStatus.PAID.value,
            kind="subscription",
            description=f"{plan.name if plan else 'Plan'} サブスクリプション（サンプル）",
            currency="jpy",
            subtotal_yen=price,
            tax_yen=tax,
            total_yen=total,
            amount_paid_yen=total,
            period_start=sub.period_start,
            period_end=sub.period_end,
            line_items_json=lines,
            paid_at=now - timedelta(days=2),
        ),
        Invoice(
            user_id=user.id,
            subscription_id=sub.id,
            number=f"INV-{now.strftime('%Y%m%d')}-S002",
            status=InvoiceStatus.OPEN.value,
            kind="renewal",
            description="次回更新予定（サンプル・未払い）",
            currency="jpy",
            subtotal_yen=price,
            tax_yen=tax,
            total_yen=total,
            amount_paid_yen=0,
            period_start=sub.period_end,
            period_end=sub.period_end + timedelta(days=30),
            line_items_json=lines,
        ),
    ]
    db.add_all(invoices)


def _ensure_notifications(db, user: User) -> None:
    existing = db.scalars(
        select(EmailNotification).where(EmailNotification.user_id == user.id).limit(1)
    ).first()
    if existing:
        return

    now = _utcnow()
    samples = [
        (
            "reservation_confirmed",
            "【Studio Reservation】予約が確定しました",
            f"{user.full_name} 様\n\n予約が確定しました（サンプル通知）。\nダッシュボードから詳細を確認できます。",
        ),
        (
            "invoice_paid",
            "【Studio Reservation】お支払い完了",
            f"{user.full_name} 様\n\n請求のお支払いを確認しました（サンプル）。",
        ),
        (
            "reservation_reminder",
            "【Studio Reservation】前日リマインド",
            f"{user.full_name} 様\n\n明日のご予約をお忘れなく（サンプル）。",
        ),
    ]
    for key, subject, body in samples:
        db.add(
            EmailNotification(
                user_id=user.id,
                to_email=user.email,
                subject=subject,
                body=body,
                template_key=key,
                status="sent",
                created_at=now,
            )
        )


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        plans = sub_service.ensure_plans(db)
        light = next((p for p in plans if p.code == "light"), None)
        standard = next((p for p in plans if p.code == "standard"), plans[0] if plans else None)
        premium = next((p for p in plans if p.code == "premium"), standard)

        for sub in db.scalars(select(Subscription).where(Subscription.plan_id.is_(None))).all():
            matched = next((p for p in plans if p.name == sub.plan_name), standard)
            if matched:
                sub.plan_id = matched.id
                sub.plan_name = matched.name
                sub.monthly_quota = matched.monthly_quota
            if not sub.status:
                sub.status = "active"
            db.add(sub)
        db.commit()

        _, member, member2 = _ensure_users(db)
        db.commit()

        # デモ会員は画面確認しやすい Premium、2人目は Light
        sub1 = _ensure_subscription(db, member, premium or standard, force_plan=True)
        sub2 = _ensure_subscription(db, member2, light or standard, force_plan=True)
        studios = _ensure_studios_and_slots(db)
        db.commit()

        # 画面確認用: 確定予約・キャンセル済みを投入
        samples = [
            (member, studios[0], f"{SAMPLE_NOTE} ポートレート撮影", ReservationStatus.CONFIRMED.value, 0),
            (member, studios[1], f"{SAMPLE_NOTE} 商品撮影", ReservationStatus.CONFIRMED.value, 2),
            (member, studios[2], f"{SAMPLE_NOTE} 自然光セッション", ReservationStatus.CONFIRMED.value, 4),
            (member, studios[0], f"{SAMPLE_NOTE} キャンセル済み枠", ReservationStatus.CANCELLED.value, 6),
            (member2, studios[1], f"{SAMPLE_NOTE} Member2 予約", ReservationStatus.CONFIRMED.value, 1),
        ]
        created = 0
        for user, studio, note, status, offset in samples:
            before = db.scalars(
                select(Reservation).where(Reservation.user_id == user.id, Reservation.note == note)
            ).first()
            res = _ensure_reservation(
                db,
                user=user,
                studio=studio,
                note=note,
                status=status,
                slot_offset=offset,
            )
            if res and not before:
                created += 1

        # 使用枠を確定予約数に合わせる
        for user, sub in ((member, sub1), (member2, sub2)):
            confirmed = len(
                db.scalars(
                    select(Reservation).where(
                        Reservation.user_id == user.id,
                        Reservation.status == ReservationStatus.CONFIRMED.value,
                    )
                ).all()
            )
            sub.used_count = confirmed
            db.add(sub)

        _ensure_invoices(db, member, sub1, premium or standard)
        _ensure_notifications(db, member)
        db.commit()

        users_n = len(db.scalars(select(User)).all())
        studios_n = len(db.scalars(select(Studio)).all())
        slots_n = len(db.scalars(select(TimeSlot)).all())
        res_n = len(db.scalars(select(Reservation)).all())
        inv_n = len(db.scalars(select(Invoice)).all())
        print(
            "Seed completed: "
            f"users={users_n} studios={studios_n} slots={slots_n} "
            f"reservations={res_n} (+{created} new) invoices={inv_n}"
        )
        print("Demo logins: member@studio.local / member1234 , admin@studio.local / admin1234")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
