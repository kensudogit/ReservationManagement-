from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.studio import Plan
from app.models.user import User
from app.schemas import (
    AdminSubscriptionUpdate,
    ChangePlanRequest,
    MessageOut,
    PlanOut,
    ReactivateRequest,
    SubscriptionOut,
)
from app.services import subscriptions as sub_service

router = APIRouter(tags=["subscriptions"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)) -> list[dict]:
    sub_service.ensure_plans(db)
    plans = db.scalars(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order.asc())
    ).all()
    return [sub_service.serialize_plan(p) for p in plans]


@router.get("/subscriptions/me", response_model=SubscriptionOut)
def my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = sub_service.get_user_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="サブスクリプションがありません")
    return sub_service.serialize_subscription(sub)


@router.post("/subscriptions/change-plan", response_model=SubscriptionOut)
def change_plan(
    payload: ChangePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = sub_service.change_plan(db, current_user, payload.plan_code)
    return sub_service.serialize_subscription(sub)


@router.post("/subscriptions/cancel", response_model=SubscriptionOut)
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = sub_service.cancel_subscription(db, current_user)
    return sub_service.serialize_subscription(sub)


@router.post("/subscriptions/reactivate", response_model=SubscriptionOut)
def reactivate_subscription(
    payload: ReactivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = sub_service.reactivate_subscription(db, current_user, payload.plan_code)
    return sub_service.serialize_subscription(sub)


@router.post("/subscriptions/renew", response_model=SubscriptionOut)
def renew_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = sub_service.renew_period(db, current_user)
    return sub_service.serialize_subscription(sub)


@router.get("/admin/subscriptions", response_model=list[SubscriptionOut])
def admin_list_subscriptions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict]:
    return sub_service.list_subscriptions(db)


@router.patch("/admin/subscriptions/{user_id}", response_model=SubscriptionOut)
def admin_update_subscription(
    user_id: int,
    payload: AdminSubscriptionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return sub_service.admin_update_subscription(
        db,
        user_id,
        plan_code=payload.plan_code,
        status=payload.status,
        auto_renew=payload.auto_renew,
        used_count=payload.used_count,
        monthly_quota=payload.monthly_quota,
    )
