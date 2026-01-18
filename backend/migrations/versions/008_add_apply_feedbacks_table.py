"""add_apply_feedbacks_table

Revision ID: 008_add_apply_feedbacks
Revises: 542d7e567590
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '008_add_apply_feedbacks'
down_revision: Union[str, None] = '542d7e567590'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create feedback_rating enum
    feedback_rating_enum = sa.Enum('bad', 'ok', 'great', name='feedback_rating')
    feedback_rating_enum.create(op.get_bind(), checkfirst=True)

    # Create apply_feedbacks table
    op.create_table(
        'apply_feedbacks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', feedback_rating_enum, nullable=False),
        sa.Column('vacancy_url', sa.Text(), nullable=True),
        sa.Column('task_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # Create indexes
    op.create_index('idx_apply_feedbacks_user_id', 'apply_feedbacks', ['user_id'])
    op.create_index('idx_apply_feedbacks_rating', 'apply_feedbacks', ['rating'])
    op.create_index('idx_apply_feedbacks_created_at', 'apply_feedbacks', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_apply_feedbacks_created_at', table_name='apply_feedbacks')
    op.drop_index('idx_apply_feedbacks_rating', table_name='apply_feedbacks')
    op.drop_index('idx_apply_feedbacks_user_id', table_name='apply_feedbacks')

    # Drop table
    op.drop_table('apply_feedbacks')

    # Drop enum
    sa.Enum(name='feedback_rating').drop(op.get_bind(), checkfirst=True)
