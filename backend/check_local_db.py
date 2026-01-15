"""Check local database structure and promo codes."""
import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
import os
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text
from src.db.session import get_session


async def check_local_db():
    """Check local database."""
    async with get_session() as session:
        try:
            # Check Alembic version
            result = await session.execute(text("SELECT * FROM alembic_version;"))
            version = result.fetchone()
            print(f"Alembic version: {version[0] if version else 'None'}")
            print()

            # Check tables
            result = await session.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
            ))
            tables = result.fetchall()
            print("Tables in local DB:")
            for table in tables:
                print(f"  - {table[0]}")
            print()

            # Check tariffs
            result = await session.execute(text(
                "SELECT id, slug, name, price, subscription_fee, period_value, period_unit FROM tariffs ORDER BY created_at;"
            ))
            tariffs = result.fetchall()
            print("Tariffs in local DB:")
            tariff_map = {}
            for tariff in tariffs:
                period = f"{tariff[5]} {tariff[6]}" if tariff[5] and tariff[6] else "N/A"
                print(f"  [{tariff[0]}]")
                print(f"    slug: {tariff[1]}, name: {tariff[2]}")
                print(f"    price: {tariff[3]} RUB, subscription_fee: {tariff[4]}, period: {period}")
                tariff_map[str(tariff[0])] = tariff[1]
            print()

            # Check promo codes
            result = await session.execute(text(
                "SELECT id, code, discount_type, discount_value, is_active, tariff_id, "
                "max_uses, uses_count, valid_from, valid_until FROM promo_codes ORDER BY created_at;"
            ))
            promos = result.fetchall()
            print(f"Promo codes in local DB ({len(promos)} total):")
            for promo in promos:
                tariff_slug = tariff_map.get(str(promo[5]), "unknown") if promo[5] else "all tariffs"
                tariff_info = f" (tariff: {tariff_slug})" if promo[5] else " (all tariffs)"
                validity = ""
                if promo[8]:
                    validity += f" from {promo[8]}"
                if promo[9]:
                    validity += f" until {promo[9]}"
                uses_info = f" uses: {promo[7]}"
                if promo[6]:
                    uses_info += f"/{promo[6]}"
                print(f"  {promo[1]}: {promo[2]} {promo[3]}{tariff_info} - active: {promo[4]}{uses_info}{validity}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_local_db())
