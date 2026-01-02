"""Add auto_renew and last_subscription_notification to users table.

Revision ID: 005_subscription_fields
Revises: 004_last_balance_notif
Create Date: 2026-01-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_subscription_fields"
down_revision: Union[str, None] = "004_last_balance_notif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add auto_renew column to users table
    op.add_column(
        "users",
        sa.Column(
            "auto_renew",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Auto-renew subscription when expiring",
        ),
    )

    # Add last_subscription_notification column to users table
    op.add_column(
        "users",
        sa.Column(
            "last_subscription_notification",
            sa.Integer(),
            nullable=True,
            comment="Days before expiry when last notification was sent",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "last_subscription_notification")
    op.drop_column("users", "auto_renew")
