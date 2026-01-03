"""Add period and fee fields to tariffs (M11).

Revision ID: 007_tariff_period_fields
Revises: 006_subscription_tx_type
Create Date: 2026-01-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_tariff_period_fields"
down_revision: Union[str, None] = "006_subscription_tx_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create period_unit enum type
    period_unit_enum = sa.Enum("hour", "day", "month", name="period_unit")
    period_unit_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns to tariffs
    op.add_column(
        "tariffs",
        sa.Column(
            "period_unit",
            period_unit_enum,
            nullable=False,
            server_default="month",
            comment="Period unit: hour/day/month",
        ),
    )
    op.add_column(
        "tariffs",
        sa.Column(
            "period_value",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of period units",
        ),
    )
    op.add_column(
        "tariffs",
        sa.Column(
            "subscription_fee",
            sa.Integer(),
            nullable=False,
            server_default="100",
            comment="Subscription fee in tokens per period",
        ),
    )
    op.add_column(
        "tariffs",
        sa.Column(
            "min_payment",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="200.00",
            comment="Minimum payment amount in RUB",
        ),
    )

    # Add check constraints
    op.create_check_constraint(
        "period_value_positive",
        "tariffs",
        "period_value > 0",
    )
    op.create_check_constraint(
        "subscription_fee_non_negative",
        "tariffs",
        "subscription_fee >= 0",
    )
    op.create_check_constraint(
        "min_payment_positive",
        "tariffs",
        "min_payment > 0",
    )

    # Create partial index for active tariffs with period
    op.create_index(
        "idx_tariffs_period",
        "tariffs",
        ["period_unit", "period_value"],
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_tariffs_period", table_name="tariffs")

    # Drop check constraints
    op.drop_constraint("min_payment_positive", "tariffs", type_="check")
    op.drop_constraint("subscription_fee_non_negative", "tariffs", type_="check")
    op.drop_constraint("period_value_positive", "tariffs", type_="check")

    # Drop columns
    op.drop_column("tariffs", "min_payment")
    op.drop_column("tariffs", "subscription_fee")
    op.drop_column("tariffs", "period_value")
    op.drop_column("tariffs", "period_unit")

    # Drop enum type
    sa.Enum(name="period_unit").drop(op.get_bind(), checkfirst=True)
