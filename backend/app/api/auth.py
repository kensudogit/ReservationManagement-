from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas import Token, UserCreate, UserOut
from app.services import subscriptions as sub_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User, db: Session | None = None) -> UserOut:
    sub = user.subscription
    sub_out = None
    if sub and db is not None:
        refreshed = sub_service.get_user_subscription(db, user.id)
        if refreshed:
            sub_out = sub_service.serialize_subscription(refreshed)
    elif sub:
        sub_out = {
            "id": sub.id,
            "user_id": sub.user_id,
            "plan_id": getattr(sub, "plan_id", None),
            "plan_code": sub.plan.code if getattr(sub, "plan", None) else None,
            "plan_name": sub.plan_name,
            "monthly_quota": sub.monthly_quota,
            "used_count": sub.used_count,
            "remaining": max(sub.monthly_quota - sub.used_count, 0),
            "period_start": sub.period_start,
            "period_end": sub.period_end,
            "status": getattr(sub, "status", "active"),
            "auto_renew": getattr(sub, "auto_renew", True),
            "is_active": sub.is_active,
            "cancelled_at": getattr(sub, "cancelled_at", None),
            "price_yen": sub.plan.price_yen if getattr(sub, "plan", None) else None,
        }
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        google_calendar_connected=user.google_calendar_connected,
        subscription=sub_out,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    exists = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if exists:
        raise HTTPException(status_code=400, detail="このメールアドレスは既に登録されています")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.MEMBER.value,
    )
    db.add(user)
    db.flush()

    if payload.plan_code:
        plan = sub_service.get_plan_by_code(db, payload.plan_code)
    else:
        plan = sub_service.get_default_plan(db)

    sub_service.create_subscription_for_user(db, user, plan, commit=True)

    user = db.scalars(
        select(User).options(joinedload(User.subscription)).where(User.id == user.id)
    ).first()
    return _user_out(user, db)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = db.scalars(select(User).where(User.email == form_data.username.lower())).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="メールまたはパスワードが違います")
    token = create_access_token(user.id, extra={"role": user.role})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    user = db.scalars(
        select(User).options(joinedload(User.subscription)).where(User.id == current_user.id)
    ).first()
    return _user_out(user, db)
