from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas import (
    BillingConfigOut,
    ChangePlanRequest,
    CheckoutRequest,
    CheckoutSessionOut,
    InvoiceOut,
    PortalSessionOut,
    ProrationPreviewOut,
)
from app.services import invoices as invoice_service
from app.services import stripe_billing

router = APIRouter(tags=["billing"])


@router.get("/billing/config", response_model=BillingConfigOut)
def billing_config() -> dict:
    return {
        "stripe_enabled": settings.stripe_enabled,
        "publishable_key": settings.stripe_publishable_key or None,
        "smtp_enabled": settings.smtp_enabled,
        "tax_rate": settings.tax_rate,
        "demo_mode": not settings.stripe_enabled,
    }


@router.post("/billing/checkout", response_model=CheckoutSessionOut)
def create_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if settings.stripe_enabled:
        return stripe_billing.create_checkout_session(db, current_user, payload.plan_code)
    return stripe_billing.create_demo_checkout(db, current_user, payload.plan_code)


@router.post("/billing/portal", response_model=PortalSessionOut)
def create_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return stripe_billing.create_portal_session(db, current_user)


@router.get("/billing/invoices", response_model=list[InvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    admin = current_user.role == UserRole.ADMIN.value
    return invoice_service.list_invoices(db, current_user, admin=admin)


@router.get("/billing/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    admin = current_user.role == UserRole.ADMIN.value
    return invoice_service.get_invoice(db, invoice_id, current_user, admin=admin)


@router.get("/billing/invoices/{invoice_id}/receipt", response_class=HTMLResponse)
def invoice_receipt(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    admin = current_user.role == UserRole.ADMIN.value
    data = invoice_service.get_invoice(db, invoice_id, current_user, admin=admin)
    return HTMLResponse(invoice_service.receipt_html(data))


@router.post("/subscriptions/change-plan/preview", response_model=ProrationPreviewOut)
def preview_change_plan(
    payload: ChangePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return invoice_service.preview_plan_change(db, current_user, payload.plan_code)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    return stripe_billing.handle_webhook(db, payload, sig)


@router.get("/billing/notifications")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    from sqlalchemy import select

    from app.models.billing import EmailNotification

    stmt = select(EmailNotification).order_by(EmailNotification.created_at.desc()).limit(50)
    if current_user.role != UserRole.ADMIN.value:
        stmt = stmt.where(EmailNotification.user_id == current_user.id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": r.id,
            "to_email": r.to_email,
            "subject": r.subject,
            "template_key": r.template_key,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]
