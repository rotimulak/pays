"""Add subscription transaction type.

Revision ID: 006_subscription_tx_type
Revises: 005_subscription_fields
Create Date: 2026-01-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_subscription_tx_type"
down_revision: Union[str, None] = "005_subscription_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'subscription' value to transaction_type enum
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'subscription'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # A full migration would require recreating the type
    pass
