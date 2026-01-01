"""Script to create the database."""
import asyncio

import asyncpg


async def create_database() -> None:
    # Connect to default 'postgres' database to create our database
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="@*decPostgres1",
        database="postgres",
    )

    try:
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            "telegram_billing",
        )

        if exists:
            print("Database 'telegram_billing' already exists")
        else:
            await conn.execute("CREATE DATABASE telegram_billing")
            print("Database 'telegram_billing' created successfully")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_database())
