from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    plan_code: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    monthly_quota: int
    price_yen: int
    sort_order: int
    is_active: bool


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int | None = None
    plan_id: int | None = None
    plan_code: str | None = None
    plan_name: str
    monthly_quota: int
    used_count: int
    remaining: int
    period_start: datetime
    period_end: datetime
    status: str = "active"
    auto_renew: bool = True
    is_active: bool
    cancelled_at: datetime | None = None
    price_yen: int | None = None
    user_name: str | None = None
    user_email: str | None = None


class ChangePlanRequest(BaseModel):
    plan_code: str


class ReactivateRequest(BaseModel):
    plan_code: str | None = None


class AdminSubscriptionUpdate(BaseModel):
    plan_code: str | None = None
    status: str | None = None
    auto_renew: bool | None = None
    used_count: int | None = None
    monthly_quota: int | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    google_calendar_connected: bool
    subscription: SubscriptionOut | None = None


class StudioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    capacity: int
    is_active: bool


class StudioCreate(BaseModel):
    name: str
    description: str | None = None
    capacity: int = 1


class TimeSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    studio_id: int
    start_at: datetime
    end_at: datetime
    is_available: bool
    studio_name: str | None = None


class ReservationCreate(BaseModel):
    time_slot_id: int
    note: str | None = None


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    studio_id: int
    time_slot_id: int
    status: str
    note: str | None
    google_event_id: str | None
    created_at: datetime
    cancelled_at: datetime | None
    studio_name: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class MessageOut(BaseModel):
    message: str


class GoogleAuthUrl(BaseModel):
    url: str
    configured: bool


class BillingConfigOut(BaseModel):
    stripe_enabled: bool
    publishable_key: str | None = None
    smtp_enabled: bool
    tax_rate: float
    demo_mode: bool


class CheckoutRequest(BaseModel):
    plan_code: str


class CheckoutSessionOut(BaseModel):
    id: str
    url: str
    mode: str
    invoice: dict | None = None


class PortalSessionOut(BaseModel):
    url: str


class InvoiceLineItem(BaseModel):
    label: str
    amount_yen: int


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subscription_id: int | None = None
    number: str
    status: str
    kind: str
    description: str | None = None
    currency: str
    subtotal_yen: int
    tax_yen: int
    total_yen: int
    amount_paid_yen: int
    proration_yen: int
    period_start: datetime | None = None
    period_end: datetime | None = None
    stripe_invoice_id: str | None = None
    hosted_invoice_url: str | None = None
    invoice_pdf_url: str | None = None
    line_items: list[InvoiceLineItem] = []
    paid_at: datetime | None = None
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None


class ProrationPreviewOut(BaseModel):
    from_plan_code: str
    from_plan_name: str
    to_plan_code: str
    to_plan_name: str
    old_price_yen: int
    new_price_yen: int
    period_start: datetime | str
    period_end: datetime | str
    remaining_days: int
    total_days: int
    unused_credit_yen: int
    new_charge_yen: int
    proration_yen: int
    tax_yen: int
    total_due_yen: int
    direction: str
    explanation: str


class ChangePlanResultOut(BaseModel):
    subscription: SubscriptionOut
    proration: ProrationPreviewOut
    invoice: InvoiceOut
