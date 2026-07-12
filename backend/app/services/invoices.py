from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.billing import Invoice, InvoiceStatus
from app.models.studio import Plan, Subscription
from app.models.user import User
from app.services import email_notify
from app.services.proration import ProrationPreview, calculate_proration
from app.services.subscriptions import (
    ensure_aware,
    get_plan_by_code,
    get_user_subscription,
    now_utc,
    serialize_subscription,
)


def _next_invoice_number(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(select(func.count()).select_from(Invoice).where(Invoice.number.like(f"INV-{today}-%"))) or 0
    return f"INV-{today}-{count + 1:04d}"


def serialize_invoice(inv: Invoice) -> dict:
    lines = []
    if inv.line_items_json:
        try:
            lines = json.loads(inv.line_items_json)
        except json.JSONDecodeError:
            lines = []
    return {
        "id": inv.id,
        "user_id": inv.user_id,
        "subscription_id": inv.subscription_id,
        "number": inv.number,
        "status": inv.status,
        "kind": inv.kind,
        "description": inv.description,
        "currency": inv.currency,
        "subtotal_yen": inv.subtotal_yen,
        "tax_yen": inv.tax_yen,
        "total_yen": inv.total_yen,
        "amount_paid_yen": inv.amount_paid_yen,
        "proration_yen": inv.proration_yen,
        "period_start": inv.period_start,
        "period_end": inv.period_end,
        "stripe_invoice_id": inv.stripe_invoice_id,
        "hosted_invoice_url": inv.hosted_invoice_url,
        "invoice_pdf_url": inv.invoice_pdf_url,
        "line_items": lines,
        "paid_at": inv.paid_at,
        "created_at": inv.created_at,
        "user_name": inv.user.full_name if inv.user else None,
        "user_email": inv.user.email if inv.user else None,
    }


def create_invoice(
    db: Session,
    *,
    user: User,
    subscription: Subscription | None,
    kind: str,
    description: str,
    subtotal_yen: int,
    tax_yen: int,
    total_yen: int,
    proration_yen: int = 0,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    line_items: list[dict] | None = None,
    status: str = InvoiceStatus.PAID.value,
    stripe_invoice_id: str | None = None,
    hosted_invoice_url: str | None = None,
    invoice_pdf_url: str | None = None,
) -> Invoice:
    paid_at = now_utc() if status == InvoiceStatus.PAID.value else None
    inv = Invoice(
        user_id=user.id,
        subscription_id=subscription.id if subscription else None,
        number=_next_invoice_number(db),
        status=status,
        kind=kind,
        description=description,
        currency="jpy",
        subtotal_yen=subtotal_yen,
        tax_yen=tax_yen,
        total_yen=total_yen,
        amount_paid_yen=total_yen if status == InvoiceStatus.PAID.value else 0,
        proration_yen=proration_yen,
        period_start=period_start,
        period_end=period_end,
        stripe_invoice_id=stripe_invoice_id,
        hosted_invoice_url=hosted_invoice_url,
        invoice_pdf_url=invoice_pdf_url,
        line_items_json=json.dumps(line_items or [], ensure_ascii=False),
        paid_at=paid_at,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def list_invoices(db: Session, user: User, *, admin: bool = False) -> list[dict]:
    stmt = select(Invoice).options(joinedload(Invoice.user)).order_by(Invoice.created_at.desc())
    if not admin:
        stmt = stmt.where(Invoice.user_id == user.id)
    rows = db.scalars(stmt.limit(100)).unique().all()
    return [serialize_invoice(r) for r in rows]


def get_invoice(db: Session, invoice_id: int, user: User, *, admin: bool = False) -> dict:
    inv = db.scalars(
        select(Invoice).options(joinedload(Invoice.user)).where(Invoice.id == invoice_id)
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="請求書が見つかりません")
    if not admin and inv.user_id != user.id:
        raise HTTPException(status_code=403, detail="権限がありません")
    return serialize_invoice(inv)


def preview_plan_change(db: Session, user: User, plan_code: str) -> dict:
    sub = get_user_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="サブスクリプションがありません")
    plan = get_plan_by_code(db, plan_code)
    if sub.plan_id == plan.id:
        raise HTTPException(status_code=400, detail="既にこのプランです")
    preview = calculate_proration(sub, plan, tax_rate=settings.tax_rate)
    return preview.to_dict()


def change_plan_with_proration(db: Session, user: User, plan_code: str) -> dict:
    sub = get_user_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="サブスクリプションがありません")
    if sub.status == "expired":
        raise HTTPException(status_code=400, detail="期限切れです。再契約してください")

    new_plan = get_plan_by_code(db, plan_code)
    if sub.plan_id == new_plan.id:
        raise HTTPException(status_code=400, detail="既にこのプランです")

    old_name = sub.plan_name
    preview = calculate_proration(sub, new_plan, tax_rate=settings.tax_rate)

    # Stripe 連携がある場合は subscription item を更新（価格 ID があるとき）
    if settings.stripe_enabled and sub.stripe_subscription_id and new_plan.stripe_price_id:
        from app.services import stripe_billing

        stripe_billing.update_subscription_plan(sub, new_plan, proration=True)

    sub.plan_id = new_plan.id
    sub.plan_name = new_plan.name
    sub.monthly_quota = new_plan.monthly_quota
    if sub.used_count > new_plan.monthly_quota:
        sub.used_count = new_plan.monthly_quota
    if sub.status == "cancelled":
        sub.status = "active"
        sub.is_active = True
        sub.auto_renew = True
        sub.cancelled_at = None
    db.add(sub)
    db.commit()

    line_items = [
        {
            "label": f"旧プラン未使用クレジット（{preview.from_plan_name}）",
            "amount_yen": -preview.unused_credit_yen,
        },
        {
            "label": f"新プラン日割り（{preview.to_plan_name} / 残{preview.remaining_days}日）",
            "amount_yen": preview.new_charge_yen,
        },
    ]
    if preview.tax_yen:
        line_items.append({"label": f"消費税（{int(settings.tax_rate * 100)}%）", "amount_yen": preview.tax_yen})

    inv = create_invoice(
        db,
        user=user,
        subscription=sub,
        kind="proration",
        description=f"プラン変更日割り: {old_name} → {new_plan.name}",
        subtotal_yen=preview.proration_yen,
        tax_yen=preview.tax_yen if preview.proration_yen > 0 else 0,
        total_yen=preview.total_due_yen,
        proration_yen=preview.proration_yen,
        period_start=ensure_aware(sub.period_start),
        period_end=ensure_aware(sub.period_end),
        line_items=line_items,
        status=InvoiceStatus.PAID.value,
    )

    email_notify.notify_plan_changed(
        db, user, old_plan=old_name, new_plan=new_plan.name, proration_yen=preview.proration_yen
    )
    if inv.total_yen != 0 or True:
        email_notify.notify_invoice_paid(db, user, invoice_number=inv.number, total_yen=inv.total_yen)

    refreshed = get_user_subscription(db, user.id, refresh_period=False)
    return {
        "subscription": serialize_subscription(refreshed),  # type: ignore[arg-type]
        "proration": preview.to_dict(),
        "invoice": serialize_invoice(inv),
    }


def create_renewal_invoice(db: Session, user: User, sub: Subscription) -> Invoice:
    price = sub.plan.price_yen if sub.plan else 0
    tax = int(round(price * settings.tax_rate))
    total = price + tax
    inv = create_invoice(
        db,
        user=user,
        subscription=sub,
        kind="renewal",
        description=f"定期更新: {sub.plan_name}",
        subtotal_yen=price,
        tax_yen=tax,
        total_yen=total,
        period_start=ensure_aware(sub.period_start),
        period_end=ensure_aware(sub.period_end),
        line_items=[
            {"label": f"{sub.plan_name} 月額", "amount_yen": price},
            {"label": f"消費税（{int(settings.tax_rate * 100)}%）", "amount_yen": tax},
        ],
    )
    email_notify.notify_renewal(db, user, plan_name=sub.plan_name, amount_yen=total)
    email_notify.notify_invoice_paid(db, user, invoice_number=inv.number, total_yen=total)
    return inv


def receipt_html(invoice: dict) -> str:
    lines = "".join(
        f"<tr><td>{item.get('label')}</td><td style='text-align:right'>¥{int(item.get('amount_yen', 0)):,}</td></tr>"
        for item in invoice.get("line_items") or []
    )
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>領収書 {invoice['number']}</title>
<style>
body{{font-family:sans-serif;max-width:720px;margin:40px auto;color:#222}}
h1{{font-size:1.6rem}} table{{width:100%;border-collapse:collapse;margin-top:24px}}
td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left}}
.total{{font-size:1.2rem;font-weight:700}}
.meta{{color:#666;line-height:1.7}}
</style></head><body>
<h1>領収書 / 請求書</h1>
<p class="meta">
請求書番号: {invoice['number']}<br>
宛名: {invoice.get('user_name') or ''}（{invoice.get('user_email') or ''}）<br>
発行日: {invoice.get('paid_at') or invoice.get('created_at')}<br>
ステータス: {invoice['status']}
</p>
<p>{invoice.get('description') or ''}</p>
<table>
<thead><tr><th>内容</th><th style="text-align:right">金額</th></tr></thead>
<tbody>{lines}</tbody>
</table>
<p class="total">合計: ¥{invoice['total_yen']:,}（税込）</p>
<p class="meta">上記正に領収いたしました。Studio Reservation Manager</p>
</body></html>"""
