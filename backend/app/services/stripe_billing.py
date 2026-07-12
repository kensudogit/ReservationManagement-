from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.studio import Plan, Subscription
from app.models.user import User
from app.services import email_notify, invoices as invoice_service
from app.services.subscriptions import get_plan_by_code, get_user_subscription, now_utc

try:
    import stripe
except ImportError:  # pragma: no cover
    stripe = None  # type: ignore


def _require_stripe():
    if not settings.stripe_enabled or stripe is None:
        raise HTTPException(status_code=400, detail="Stripe が設定されていません（デモ課金モードで利用できます）")
    stripe.api_key = settings.stripe_secret_key


def ensure_customer(db: Session, user: User) -> str:
    _require_stripe()
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, name=user.full_name, metadata={"user_id": str(user.id)})
    user.stripe_customer_id = customer["id"]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.stripe_customer_id  # type: ignore[return-value]


def create_checkout_session(db: Session, user: User, plan_code: str) -> dict:
    _require_stripe()
    plan = get_plan_by_code(db, plan_code)
    if not plan.stripe_price_id:
        raise HTTPException(
            status_code=400,
            detail=f"プラン {plan.code} に stripe_price_id が未設定です。Stripe Dashboard で Price を作成し DB に登録してください。",
        )

    customer_id = ensure_customer(db, user)
    success = settings.stripe_success_url or f"{settings.frontend_url}/subscription?checkout=success"
    cancel = settings.stripe_cancel_url or f"{settings.frontend_url}/subscription?checkout=cancel"

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=success,
        cancel_url=cancel,
        metadata={"user_id": str(user.id), "plan_code": plan.code},
        subscription_data={"metadata": {"user_id": str(user.id), "plan_code": plan.code}},
    )
    return {"id": session["id"], "url": session["url"], "mode": "stripe"}


def create_demo_checkout(db: Session, user: User, plan_code: str) -> dict:
    """Stripe 未設定時のデモ課金。即時にプラン適用 + 請求書発行。"""
    from app.services import subscriptions as sub_service

    plan = get_plan_by_code(db, plan_code)
    sub = get_user_subscription(db, user.id, refresh_period=False)
    if not sub:
        sub = sub_service.create_subscription_for_user(db, user, plan)
    else:
        sub.plan_id = plan.id
        sub.plan_name = plan.name
        sub.monthly_quota = plan.monthly_quota
        sub.status = "active"
        sub.is_active = True
        sub.auto_renew = True
        sub.cancelled_at = None
        sub.period_start = now_utc()
        from datetime import timedelta

        from app.services.subscriptions import PERIOD_DAYS

        sub.period_end = sub.period_start + timedelta(days=PERIOD_DAYS)
        sub.used_count = 0
        db.add(sub)
        db.commit()

    tax = int(round(plan.price_yen * settings.tax_rate))
    total = plan.price_yen + tax
    inv = invoice_service.create_invoice(
        db,
        user=user,
        subscription=sub,
        kind="subscription",
        description=f"サブスク開始（デモ決済）: {plan.name}",
        subtotal_yen=plan.price_yen,
        tax_yen=tax,
        total_yen=total,
        period_start=sub.period_start,
        period_end=sub.period_end,
        line_items=[
            {"label": f"{plan.name} 月額", "amount_yen": plan.price_yen},
            {"label": f"消費税（{int(settings.tax_rate * 100)}%）", "amount_yen": tax},
        ],
    )
    email_notify.notify_invoice_paid(db, user, invoice_number=inv.number, total_yen=total)
    email_notify.notify_renewal(db, user, plan_name=plan.name, amount_yen=total)
    return {
        "id": f"demo_{inv.number}",
        "url": f"{settings.frontend_url}/subscription/invoices/{inv.id}?paid=1",
        "mode": "demo",
        "invoice": invoice_service.serialize_invoice(inv),
    }


def create_portal_session(db: Session, user: User) -> dict:
    _require_stripe()
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Stripe 顧客がありません。先にチェックアウトしてください。")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/subscription",
    )
    return {"url": session["url"]}


def update_subscription_plan(sub: Subscription, new_plan: Plan, *, proration: bool = True) -> None:
    _require_stripe()
    if not sub.stripe_subscription_id:
        return
    subscription = stripe.Subscription.retrieve(sub.stripe_subscription_id)
    item_id = sub.stripe_subscription_item_id or subscription["items"]["data"][0]["id"]
    stripe.Subscription.modify(
        sub.stripe_subscription_id,
        items=[{"id": item_id, "price": new_plan.stripe_price_id}],
        proration_behavior="create_prorations" if proration else "none",
        metadata={"plan_code": new_plan.code},
    )


def cancel_stripe_subscription(sub: Subscription, *, at_period_end: bool = True) -> None:
    if not settings.stripe_enabled or not sub.stripe_subscription_id or stripe is None:
        return
    stripe.api_key = settings.stripe_secret_key
    if at_period_end:
        stripe.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=True)
    else:
        stripe.Subscription.cancel(sub.stripe_subscription_id)


def _on_invoice_paid(db: Session, invoice: dict) -> None:
    from sqlalchemy import select

    from app.models.billing import Invoice

    customer_id = invoice.get("customer")
    user = None
    if customer_id:
        user = db.scalars(select(User).where(User.stripe_customer_id == customer_id)).first()
    if not user:
        return
    sub = get_user_subscription(db, user.id, refresh_period=False)
    amount = int(invoice.get("amount_paid") or 0)
    if invoice.get("id"):
        existing = db.scalars(select(Invoice).where(Invoice.stripe_invoice_id == invoice["id"])).first()
        if existing:
            return
    inv = invoice_service.create_invoice(
        db,
        user=user,
        subscription=sub,
        kind="subscription",
        description=invoice.get("description") or "Stripe 請求",
        subtotal_yen=amount,
        tax_yen=0,
        total_yen=amount,
        stripe_invoice_id=invoice.get("id"),
        hosted_invoice_url=invoice.get("hosted_invoice_url"),
        invoice_pdf_url=invoice.get("invoice_pdf"),
        line_items=[{"label": "Stripe invoice", "amount_yen": amount}],
    )
    email_notify.notify_invoice_paid(db, user, invoice_number=inv.number, total_yen=amount)


def _on_invoice_failed(db: Session, invoice: dict) -> None:
    from sqlalchemy import select

    customer_id = invoice.get("customer")
    user = None
    if customer_id:
        user = db.scalars(select(User).where(User.stripe_customer_id == customer_id)).first()
    if not user:
        return
    email_notify.notify_payment_failed(db, user, reason="Stripe invoice.payment_failed")
    sub = get_user_subscription(db, user.id, refresh_period=False)
    if sub:
        sub.status = "past_due"
        db.add(sub)
        db.commit()


def handle_webhook(db: Session, payload: bytes, sig_header: str) -> dict:
    import json

    _require_stripe()
    try:
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
            etype = event["type"]
            data = event["data"]["object"]
        else:
            event = json.loads(payload.decode("utf-8"))
            etype = event["type"]
            data = event["data"]["object"]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Webhook 検証失敗: {exc}") from exc

    if etype == "checkout.session.completed":
        _on_checkout_completed(db, data)
    elif etype in {"invoice.paid", "invoice.payment_succeeded"}:
        _on_invoice_paid(db, data)
    elif etype == "invoice.payment_failed":
        _on_invoice_failed(db, data)
    elif etype == "customer.subscription.deleted":
        _on_subscription_deleted(db, data)

    return {"received": True, "type": etype}


def _on_checkout_completed(db: Session, session: dict) -> None:
    from datetime import timedelta

    from app.services.subscriptions import PERIOD_DAYS, create_subscription_for_user

    meta = session.get("metadata") or {}
    user_id = int(meta.get("user_id") or 0)
    plan_code = meta.get("plan_code")
    if not user_id or not plan_code:
        return
    user = db.get(User, user_id)
    if not user:
        return
    plan = get_plan_by_code(db, plan_code)
    sub = get_user_subscription(db, user.id, refresh_period=False)
    if not sub:
        sub = create_subscription_for_user(db, user, plan)
    else:
        sub.plan_id = plan.id
        sub.plan_name = plan.name
        sub.monthly_quota = plan.monthly_quota
        sub.status = "active"
        sub.is_active = True
        sub.auto_renew = True
        sub.period_start = now_utc()
        sub.period_end = sub.period_start + timedelta(days=PERIOD_DAYS)
        sub.used_count = 0
    if session.get("subscription"):
        sub.stripe_subscription_id = session["subscription"]
    if session.get("customer"):
        user.stripe_customer_id = session["customer"]
        db.add(user)
    db.add(sub)
    db.commit()


def _on_subscription_deleted(db: Session, subscription: dict) -> None:
    from sqlalchemy import select

    sub = db.scalars(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription.get("id"))
    ).first()
    if not sub:
        return
    sub.status = "cancelled"
    sub.auto_renew = False
    sub.cancelled_at = now_utc()
    db.add(sub)
    db.commit()
    user = db.get(User, sub.user_id)
    if user:
        email_notify.notify_subscription_cancelled(db, user, period_end=str(sub.period_end))
