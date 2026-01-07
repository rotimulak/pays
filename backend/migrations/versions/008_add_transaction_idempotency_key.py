"""Add idempotency_key to transactions table.

Revision ID: 008_tx_idempotency_key
Revises: 007_tariff_period_fields
Create Date: 2026-01-07 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_tx_idempotency_key"
down_revision: Union[str, None] = "007_tariff_period_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add idempotency_key column to transactions
    op.add_column(
        "transactions",
        sa.Column(
            "idempotency_key",
            sa.Text(),
            nullable=True,
            comment="Idempotency key for deduplication",
        ),
    )

    # Add unique constraint for idempotency_key
    op.create_unique_constraint(
        "uq_transactions_idempotency_key",
        "transactions",
        ["idempotency_key"],
    )


def downgrade() -> None:
    # Drop unique constraint
    op.drop_constraint(
        "uq_transactions_idempotency_key",
        "transactions",
        type_="unique",
    )

    # Drop column
    op.drop_column("transactions", "idempotency_key")
