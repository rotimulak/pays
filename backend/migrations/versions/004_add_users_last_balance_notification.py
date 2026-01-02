"""Add last_balance_notification column to users table.

Revision ID: 004_last_balance_notif
Revises: 002_add_bonus_tokens
Create Date: 2026-01-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_last_balance_notif"
down_revision: Union[str, None] = "002_add_bonus_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_balance_notification column to users table
    op.add_column(
        "users",
        sa.Column(
            "last_balance_notification",
            sa.Integer(),
            nullable=True,
            comment="Last balance threshold notification was sent for",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "last_balance_notification")
