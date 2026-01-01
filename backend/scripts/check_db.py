"""Script to check database tables."""
import asyncio

import asyncpg


async def check_database() -> None:
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="@*decPostgres1",
        database="telegram_billing",
    )

    try:
        # List all tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        print("Tables created:")
        for t in tables:
            print(f"  - {t['tablename']}")

        # List ENUMs
        enums = await conn.fetch("""
            SELECT typname FROM pg_type
            WHERE typcategory = 'E'
            ORDER BY typname
        """)

        print("\nENUM types:")
        for e in enums:
            print(f"  - {e['typname']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_database())
