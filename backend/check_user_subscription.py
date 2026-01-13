"""Check user subscription status."""
import asyncio
import os
from datetime import datetime
import asyncpg


async def check_users():
    """Check users subscription status."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/telegram_billing"
    ).replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)

    try:
        rows = await conn.fetch("""
            SELECT
                id,
                username,
                first_name,
                token_balance,
                subscription_end,
                is_blocked
            FROM users
        """)

        if not rows:
            print("[!] No users found")
            return

        print(f"[*] Found {len(rows)} users:\n")

        now = datetime.utcnow()
        for row in rows:
            sub_status = "INACTIVE"
            if row['subscription_end'] and row['subscription_end'] > now:
                sub_status = "ACTIVE"

            print(f"User ID: {row['id']}")
            print(f"  Username: {row['username']}")
            print(f"  Name: {row['first_name']}")
            print(f"  Balance: {row['token_balance']}")
            print(f"  Subscription: {sub_status}")
            print(f"  Sub End: {row['subscription_end']}")
            print(f"  Blocked: {row['is_blocked']}")
            print()

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_users())
