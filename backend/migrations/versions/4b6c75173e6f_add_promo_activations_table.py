"""add_promo_activations_table

Revision ID: 4b6c75173e6f
Revises: 007_tariff_period_fields
Create Date: 2026-01-12 16:14:42.096476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b6c75173e6f'
down_revision: Union[str, None] = '007_tariff_period_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create promo_activations table
    op.create_table(
        'promo_activations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tariff_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('tariffs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('promo_code_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('promo_codes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('tokens_credited', sa.Integer(), nullable=False),
        sa.Column('subscription_days_added', sa.Integer(), nullable=False),
        sa.CheckConstraint('tokens_credited >= 0', name='tokens_credited_non_negative'),
        sa.CheckConstraint('subscription_days_added >= 0', name='subscription_days_non_negative'),
    )

    # Create indexes
    op.create_index('idx_promo_activations_user_tariff', 'promo_activations', ['user_id', 'tariff_id'], unique=True)
    op.create_index('idx_promo_activations_user_id', 'promo_activations', ['user_id'])
    op.create_index('idx_promo_activations_promo_code_id', 'promo_activations', ['promo_code_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_promo_activations_promo_code_id', 'promo_activations')
    op.drop_index('idx_promo_activations_user_id', 'promo_activations')
    op.drop_index('idx_promo_activations_user_tariff', 'promo_activations')

    # Drop table
    op.drop_table('promo_activations')
