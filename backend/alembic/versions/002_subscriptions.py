"""initial plans + subscription enhancements

Revision ID: 002_subscriptions
Revises: 001_initial
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_subscriptions"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_quota", sa.Integer(), nullable=False),
        sa.Column("price_yen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    op.add_column("subscriptions", sa.Column("plan_id", sa.Integer(), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "subscriptions",
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("subscriptions", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_subscriptions_plan_id", "subscriptions", "plans", ["plan_id"], ["id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_constraint("fk_subscriptions_plan_id", "subscriptions", type_="foreignkey")
    op.drop_column("subscriptions", "cancelled_at")
    op.drop_column("subscriptions", "auto_renew")
    op.drop_column("subscriptions", "status")
    op.drop_column("subscriptions", "plan_id")
    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")
