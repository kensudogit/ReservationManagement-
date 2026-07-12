"""billing schema

Revision ID: 003_billing
Revises: 002_subscriptions
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_billing"
down_revision: Union[str, None] = "002_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(120), nullable=True))
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"])

    op.add_column("plans", sa.Column("stripe_price_id", sa.String(120), nullable=True))

    op.add_column("subscriptions", sa.Column("stripe_subscription_id", sa.String(120), nullable=True))
    op.add_column("subscriptions", sa.Column("stripe_subscription_item_id", sa.String(120), nullable=True))
    op.create_index("ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="jpy"),
        sa.Column("subtotal_yen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tax_yen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_yen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("amount_paid_yen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proration_yen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(120), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(120), nullable=True),
        sa.Column("hosted_invoice_url", sa.Text(), nullable=True),
        sa.Column("invoice_pdf_url", sa.Text(), nullable=True),
        sa.Column("line_items_json", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"])
    op.create_index("ix_invoices_number", "invoices", ["number"], unique=True)
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_stripe_invoice_id", "invoices", ["stripe_invoice_id"])

    op.create_table(
        "email_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("template_key", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_notifications_user_id", "email_notifications", ["user_id"])
    op.create_index("ix_email_notifications_template_key", "email_notifications", ["template_key"])


def downgrade() -> None:
    op.drop_table("email_notifications")
    op.drop_table("invoices")
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_column("subscriptions", "stripe_subscription_item_id")
    op.drop_column("subscriptions", "stripe_subscription_id")
    op.drop_column("plans", "stripe_price_id")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "stripe_customer_id")
