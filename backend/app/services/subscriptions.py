from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.studio import Plan, Subscription, SubscriptionStatus
from app.models.user import User

DEFAULT_PLAN_CODE = "standard"
PERIOD_DAYS = 30

DEFAULT_PLANS = [
    {
        "code": "light",
        "name": "Light",
        "description": "ライト利用向け。月2枠まで予約可能。",
        "monthly_quota": 2,
        "price_yen": 9800,
        "sort_order": 10,
    },
    {
        "code": "standard",
        "name": "Standard",
        "description": "標準プラン。月4枠まで予約可能。",
        "monthly_quota": 4,
        "price_yen": 19800,
        "sort_order": 20,
    },
    {
        "code": "premium",
        "name": "Premium",
        "description": "ヘビーユーザー向け。月8枠まで予約可能。",
        "monthly_quota": 8,
        "price_yen": 34800,
        "sort_order": 30,
    },
    {
        "code": "unlimited",
        "name": "Unlimited",
        "description": "スタジオ常連向け。月20枠まで予約可能。",
        "monthly_quota": 20,
        "price_yen": 59800,
        "sort_order": 40,
    },
]


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_plans(db: Session) -> list[Plan]:
    created = False
    for item in DEFAULT_PLANS:
        existing = db.scalars(select(Plan).where(Plan.code == item["code"])).first()
        if existing:
            existing.name = item["name"]
            existing.description = item["description"]
            existing.monthly_quota = item["monthly_quota"]
            existing.price_yen = item["price_yen"]
            existing.sort_order = item["sort_order"]
            existing.is_active = True
            db.add(existing)
        else:
            db.add(Plan(**item, is_active=True))
            created = True
    db.commit()
    return list(db.scalars(select(Plan).order_by(Plan.sort_order.asc())).all())


def get_plan_by_code(db: Session, code: str) -> Plan:
    plan = db.scalars(select(Plan).where(Plan.code == code, Plan.is_active.is_(True))).first()
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    return plan


def get_default_plan(db: Session) -> Plan:
    ensure_plans(db)
    return get_plan_by_code(db, DEFAULT_PLAN_CODE)


def serialize_subscription(sub: Subscription) -> dict:
    remaining = max(sub.monthly_quota - sub.used_count, 0)
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "plan_id": sub.plan_id,
        "plan_code": sub.plan.code if sub.plan else None,
        "plan_name": sub.plan_name,
        "monthly_quota": sub.monthly_quota,
        "used_count": sub.used_count,
        "remaining": remaining,
        "period_start": sub.period_start,
        "period_end": sub.period_end,
        "status": sub.status,
        "auto_renew": sub.auto_renew,
        "is_active": sub.is_active,
        "cancelled_at": sub.cancelled_at,
        "price_yen": sub.plan.price_yen if sub.plan else None,
        "user_name": sub.user.full_name if sub.user else None,
        "user_email": sub.user.email if sub.user else None,
    }


def serialize_plan(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "monthly_quota": plan.monthly_quota,
        "price_yen": plan.price_yen,
        "sort_order": plan.sort_order,
        "is_active": plan.is_active,
    }


def create_subscription_for_user(
    db: Session,
    user: User,
    plan: Plan | None = None,
    *,
    commit: bool = True,
) -> Subscription:
    plan = plan or get_default_plan(db)
    now = now_utc()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        plan_name=plan.name,
        monthly_quota=plan.monthly_quota,
        used_count=0,
        period_start=now,
        period_end=now + timedelta(days=PERIOD_DAYS),
        status=SubscriptionStatus.ACTIVE.value,
        auto_renew=True,
        is_active=True,
        cancelled_at=None,
    )
    db.add(sub)
    if commit:
        db.commit()
        db.refresh(sub)
    return sub


def apply_period_rules(db: Session, sub: Subscription, *, commit: bool = True) -> Subscription:
    """期間終了時に自動更新、または期限切れにする。"""
    now = now_utc()
    end = ensure_aware(sub.period_end)

    if sub.status == SubscriptionStatus.CANCELLED.value:
        if now >= end:
            sub.status = SubscriptionStatus.EXPIRED.value
            sub.is_active = False
            db.add(sub)
            if commit:
                db.commit()
                db.refresh(sub)
        return sub

    if now < end:
        return sub

    if sub.auto_renew and sub.status == SubscriptionStatus.ACTIVE.value:
        # 複数期間分まとめて進める
        while ensure_aware(sub.period_end) <= now:
            sub.period_start = ensure_aware(sub.period_end)
            sub.period_end = sub.period_start + timedelta(days=PERIOD_DAYS)
        sub.used_count = 0
        sub.is_active = True
        sub.status = SubscriptionStatus.ACTIVE.value
    else:
        sub.status = SubscriptionStatus.EXPIRED.value
        sub.is_active = False

    db.add(sub)
    if commit:
        db.commit()
        db.refresh(sub)
    return sub


def get_user_subscription(db: Session, user_id: int, *, refresh_period: bool = True) -> Subscription | None:
    sub = db.scalars(
        select(Subscription)
        .options(joinedload(Subscription.plan), joinedload(Subscription.user))
        .where(Subscription.user_id == user_id)
    ).first()
    if not sub:
        return None
    if refresh_period:
        sub = apply_period_rules(db, sub)
        sub = db.scalars(
            select(Subscription)
            .options(joinedload(Subscription.plan), joinedload(Subscription.user))
            .where(Subscription.id == sub.id)
        ).first()
    return sub


def require_bookable_subscription(db: Session, user_id: int) -> Subscription:
    sub = get_user_subscription(db, user_id)
    if not sub or not sub.is_active or sub.status != SubscriptionStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="有効なサブスクリプションがありません")
    if now_utc() >= ensure_aware(sub.period_end):
        raise HTTPException(status_code=400, detail="契約期間が終了しています。プランを更新してください")
    if sub.used_count >= sub.monthly_quota:
        raise HTTPException(status_code=400, detail="今月の予約枠を使い切りました")
    return sub


def change_plan(db: Session, user: User, plan_code: str) -> Subscription:
    sub = get_user_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="サブスクリプションがありません")
    if sub.status == SubscriptionStatus.EXPIRED.value:
        raise HTTPException(status_code=400, detail="期限切れです。再契約してください")

    plan = get_plan_by_code(db, plan_code)
    if sub.plan_id == plan.id:
        raise HTTPException(status_code=400, detail="既にこのプランです")

    # ダウングレード時、利用済みが新枠を超えていれば used_count を枠上限に合わせる
    sub.plan_id = plan.id
    sub.plan_name = plan.name
    sub.monthly_quota = plan.monthly_quota
    if sub.used_count > plan.monthly_quota:
        sub.used_count = plan.monthly_quota
    if sub.status == SubscriptionStatus.CANCELLED.value:
        # プラン変更時は継続意思とみなして再有効化
        sub.status = SubscriptionStatus.ACTIVE.value
        sub.is_active = True
        sub.auto_renew = True
        sub.cancelled_at = None

    db.add(sub)
    db.commit()
    return get_user_subscription(db, user.id, refresh_period=False)  # type: ignore[return-value]


def cancel_subscription(db: Session, user: User) -> Subscription:
    sub = get_user_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="サブスクリプションがありません")
    if sub.status != SubscriptionStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="有効な契約ではありません")

    sub.auto_renew = False
    sub.status = SubscriptionStatus.CANCELLED.value
    sub.cancelled_at = now_utc()
    # 期間終了までは残枠利用可
    sub.is_active = True
    db.add(sub)
    db.commit()
    return get_user_subscription(db, user.id, refresh_period=False)  # type: ignore[return-value]


def reactivate_subscription(db: Session, user: User, plan_code: str | None = None) -> Subscription:
    sub = get_user_subscription(db, user.id, refresh_period=False)
    plan = get_plan_by_code(db, plan_code) if plan_code else None

    if not sub:
        return create_subscription_for_user(db, user, plan)

    if plan:
        sub.plan_id = plan.id
        sub.plan_name = plan.name
        sub.monthly_quota = plan.monthly_quota

    now = now_utc()
    if ensure_aware(sub.period_end) <= now or sub.status == SubscriptionStatus.EXPIRED.value:
        sub.period_start = now
        sub.period_end = now + timedelta(days=PERIOD_DAYS)
        sub.used_count = 0

    sub.status = SubscriptionStatus.ACTIVE.value
    sub.auto_renew = True
    sub.is_active = True
    sub.cancelled_at = None
    db.add(sub)
    db.commit()
    return get_user_subscription(db, user.id, refresh_period=False)  # type: ignore[return-value]


def renew_period(db: Session, user: User) -> Subscription:
    """手動で次の期間へ更新（残枠リセット）。"""
    sub = get_user_subscription(db, user.id, refresh_period=False)
    if not sub:
        raise HTTPException(status_code=404, detail="サブスクリプションがありません")
    if sub.status == SubscriptionStatus.EXPIRED.value and not sub.auto_renew:
        raise HTTPException(status_code=400, detail="期限切れです。再契約してください")

    now = now_utc()
    base = max(now, ensure_aware(sub.period_end))
    sub.period_start = base if base > now else now
    if ensure_aware(sub.period_end) > now and sub.status == SubscriptionStatus.ACTIVE.value:
        # 期間中の手動更新は次期開始を現終了日に合わせる
        sub.period_start = ensure_aware(sub.period_end)
    else:
        sub.period_start = now
    sub.period_end = sub.period_start + timedelta(days=PERIOD_DAYS)
    sub.used_count = 0
    sub.status = SubscriptionStatus.ACTIVE.value
    sub.auto_renew = True
    sub.is_active = True
    sub.cancelled_at = None
    db.add(sub)
    db.commit()
    return get_user_subscription(db, user.id, refresh_period=False)  # type: ignore[return-value]


def list_subscriptions(db: Session) -> list[dict]:
    ensure_plans(db)
    rows = db.scalars(
        select(Subscription)
        .options(joinedload(Subscription.plan), joinedload(Subscription.user))
        .order_by(Subscription.id.asc())
    ).unique().all()
    result = []
    for sub in rows:
        apply_period_rules(db, sub, commit=True)
        refreshed = db.scalars(
            select(Subscription)
            .options(joinedload(Subscription.plan), joinedload(Subscription.user))
            .where(Subscription.id == sub.id)
        ).first()
        if refreshed:
            result.append(serialize_subscription(refreshed))
    return result


def admin_update_subscription(
    db: Session,
    user_id: int,
    *,
    plan_code: str | None = None,
    status: str | None = None,
    auto_renew: bool | None = None,
    used_count: int | None = None,
    monthly_quota: int | None = None,
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    sub = get_user_subscription(db, user_id, refresh_period=False)
    if not sub:
        plan = get_plan_by_code(db, plan_code) if plan_code else get_default_plan(db)
        sub = create_subscription_for_user(db, user, plan)

    if plan_code:
        plan = get_plan_by_code(db, plan_code)
        sub.plan_id = plan.id
        sub.plan_name = plan.name
        sub.monthly_quota = plan.monthly_quota

    if monthly_quota is not None:
        if monthly_quota < 0:
            raise HTTPException(status_code=400, detail="枠数は0以上である必要があります")
        sub.monthly_quota = monthly_quota

    if used_count is not None:
        if used_count < 0:
            raise HTTPException(status_code=400, detail="利用数は0以上である必要があります")
        sub.used_count = min(used_count, sub.monthly_quota)

    if auto_renew is not None:
        sub.auto_renew = auto_renew

    if status is not None:
        if status not in {s.value for s in SubscriptionStatus}:
            raise HTTPException(status_code=400, detail="不正なステータスです")
        sub.status = status
        if status == SubscriptionStatus.ACTIVE.value:
            sub.is_active = True
            sub.cancelled_at = None
            sub.auto_renew = True if auto_renew is None else auto_renew
        elif status == SubscriptionStatus.CANCELLED.value:
            sub.auto_renew = False
            sub.cancelled_at = sub.cancelled_at or now_utc()
            sub.is_active = ensure_aware(sub.period_end) > now_utc()
        elif status == SubscriptionStatus.EXPIRED.value:
            sub.is_active = False
            sub.auto_renew = False

    db.add(sub)
    db.commit()
    refreshed = get_user_subscription(db, user_id, refresh_period=True)
    return serialize_subscription(refreshed)  # type: ignore[arg-type]
