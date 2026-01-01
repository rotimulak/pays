"""Add bonus_tokens to discount_type enum.

Revision ID: 002_add_bonus_tokens
Revises: 001_initial
Create Date: 2026-01-01 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_bonus_tokens"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new value to discount_type enum
    op.execute("ALTER TYPE discount_type ADD VALUE IF NOT EXISTS 'bonus_tokens'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly.
    # The downgrade would require recreating the enum, which is complex
    # and could fail if bonus_tokens is in use.
    # For production safety, we leave the value in place.
    pass
