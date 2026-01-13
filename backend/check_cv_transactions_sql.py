"""Проверка транзакций по анализу CV через SQL."""
import asyncio
import os
import asyncpg


async def check_cv_transactions():
    """Проверить последние транзакции по анализу CV."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/telegram_billing"
    )

    # Убираем +asyncpg если есть
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)

    try:
        # Последние 20 транзакций (все)
        rows = await conn.fetch("""
            SELECT
                u.id as telegram_id,
                t.type,
                t.tokens_delta,
                t.balance_after,
                t.description,
                t.created_at,
                t.metadata
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
            LIMIT 20
        """)

        if not rows:
            print("[!] Tranzakcij ne najdeno voobsche")
            # Проверяем есть ли вообще пользователи и транзакции
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            tx_count = await conn.fetchval("SELECT COUNT(*) FROM transactions")
            print(f"    Users: {user_count}, Transactions: {tx_count}")
            return

        print(f"[*] Najdeno {len(rows)} tranzakcij:\n")

        for row in rows:
            print(f"User: {row['telegram_id']}")
            print(f"  Type: {row['type']}")
            print(f"  Tokens Delta: {row['tokens_delta']}")
            print(f"  Balance After: {row['balance_after']}")
            print(f"  Description: {row['description']}")
            print(f"  Created: {row['created_at']}")
            print(f"  Metadata: {row['metadata']}")
            print()

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_cv_transactions())
