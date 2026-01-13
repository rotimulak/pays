"""support_fractional_tokens_and_negative_balance

Revision ID: 542d7e567590
Revises: 4b6c75173e6f
Create Date: 2026-01-13 13:48:20.424982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '542d7e567590'
down_revision: Union[str, None] = '4b6c75173e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Изменить тип колонки token_balance на Float
    op.alter_column('users', 'token_balance',
                    type_=sa.Float(),
                    existing_type=sa.Integer(),
                    existing_nullable=False,
                    postgresql_using='token_balance::float')

    # Убрать старый constraint (if exists) и добавить новый с лимитом -1000
    # Используем raw SQL для "DROP CONSTRAINT IF EXISTS"
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS token_balance_non_negative')

    op.create_check_constraint(
        'token_balance_limit',
        'users',
        'token_balance >= -1000.0'
    )

    # Изменить типы в transactions
    op.alter_column('transactions', 'tokens_delta',
                    type_=sa.Float(),
                    existing_type=sa.Integer(),
                    existing_nullable=False,
                    postgresql_using='tokens_delta::float')

    op.alter_column('transactions', 'balance_after',
                    type_=sa.Float(),
                    existing_type=sa.Integer(),
                    existing_nullable=False,
                    postgresql_using='balance_after::float')


def downgrade() -> None:
    # Обратная миграция - вернуть Integer типы
    op.alter_column('users', 'token_balance',
                    type_=sa.Integer(),
                    existing_type=sa.Float(),
                    existing_nullable=False,
                    postgresql_using='round(token_balance)::integer')

    # Вернуть старый constraint
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS token_balance_limit')

    op.create_check_constraint(
        'token_balance_non_negative',
        'users',
        'token_balance >= 0'
    )

    # Вернуть Integer типы в transactions
    op.alter_column('transactions', 'tokens_delta',
                    type_=sa.Integer(),
                    existing_type=sa.Float(),
                    existing_nullable=False,
                    postgresql_using='round(tokens_delta)::integer')

    op.alter_column('transactions', 'balance_after',
                    type_=sa.Integer(),
                    existing_type=sa.Float(),
                    existing_nullable=False,
                    postgresql_using='round(balance_after)::integer')
