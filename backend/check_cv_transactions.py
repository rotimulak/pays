"""Проверка транзакций по анализу CV."""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем src в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from db.models.transaction import Transaction
from db.models.user import User


async def check_cv_transactions():
    """Проверить последние транзакции по анализу CV."""
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_billing")

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Последние 10 транзакций с анализом CV
        stmt = (
            select(Transaction, User.telegram_id)
            .join(User, Transaction.user_id == User.id)
            .where(Transaction.description.like("%CV%"))
            .order_by(Transaction.created_at.desc())
            .limit(10)
        )

        result = await session.execute(stmt)
        rows = result.all()

        if not rows:
            print("❌ Транзакций с анализом CV не найдено")
            return

        print(f"📊 Найдено {len(rows)} транзакций:\n")

        for tx, telegram_id in rows:
            print(f"User: {telegram_id}")
            print(f"  Amount: {tx.amount}")
            print(f"  Description: {tx.description}")
            print(f"  Created: {tx.created_at}")
            print(f"  Metadata: {tx.metadata}")
            print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_cv_transactions())
