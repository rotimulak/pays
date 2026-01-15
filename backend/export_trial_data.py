"""Export trial tariff and FRIENDLY promo code data."""
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


async def export_trial_data():
    """Export trial tariff and FRIENDLY promo code."""
    async with get_session() as session:
        try:
            # Get trial-30-7 tariff
            result = await session.execute(text(
                "SELECT id, slug, name, description, price, tokens, "
                "subscription_fee, min_payment, period_value, period_unit, "
                "is_active, created_at, updated_at "
                "FROM tariffs WHERE slug = 'trial-30-7';"
            ))
            tariff = result.fetchone()

            if tariff:
                print("=== TRIAL-30-7 TARIFF ===")
                print(f"ID: {tariff[0]}")
                print(f"Slug: {tariff[1]}")
                print(f"Name: {tariff[2]}")
                print(f"Description: {tariff[3]}")
                print(f"Price: {tariff[4]}")
                print(f"Tokens: {tariff[5]}")
                print(f"Subscription Fee: {tariff[6]}")
                print(f"Min Payment: {tariff[7]}")
                print(f"Period Value: {tariff[8]}")
                print(f"Period Unit: {tariff[9]}")
                print(f"Is Active: {tariff[10]}")
                print(f"Created At: {tariff[11]}")
                print(f"Updated At: {tariff[12]}")
                print()

                # Generate SQL INSERT
                print("=== SQL INSERT FOR TRIAL-30-7 ===")
                desc = tariff[3].replace("'", "''") if tariff[3] else None
                desc_sql = f"'{desc}'" if desc else "NULL"

                print(f"""INSERT INTO tariffs (id, slug, name, description, price, tokens, subscription_fee, min_payment, period_value, period_unit, is_active, created_at, updated_at)
VALUES (
    '{tariff[0]}',
    '{tariff[1]}',
    '{tariff[2]}',
    {desc_sql},
    {tariff[4]},
    {tariff[5]},
    {tariff[6]},
    {tariff[7]},
    {tariff[8]},
    '{tariff[9]}',
    {tariff[10]},
    '{tariff[11]}',
    '{tariff[12]}'
);""")
                print()
            else:
                print("ERROR: trial-30-7 tariff not found!")
                return

            # Get FRIENDLY promo code
            result = await session.execute(text(
                "SELECT id, code, discount_type, discount_value, max_uses, uses_count, "
                "valid_from, valid_until, tariff_id, is_active, created_at, updated_at "
                "FROM promo_codes WHERE code = 'FRIENDLY';"
            ))
            promo = result.fetchone()

            if promo:
                print("=== FRIENDLY PROMO CODE ===")
                print(f"ID: {promo[0]}")
                print(f"Code: {promo[1]}")
                print(f"Discount Type: {promo[2]}")
                print(f"Discount Value: {promo[3]}")
                print(f"Max Uses: {promo[4]}")
                print(f"Uses Count: {promo[5]}")
                print(f"Valid From: {promo[6]}")
                print(f"Valid Until: {promo[7]}")
                print(f"Tariff ID: {promo[8]}")
                print(f"Is Active: {promo[9]}")
                print(f"Created At: {promo[10]}")
                print(f"Updated At: {promo[11]}")
                print()

                # Generate SQL INSERT
                print("=== SQL INSERT FOR FRIENDLY ===")
                valid_until_sql = f"'{promo[7]}'" if promo[7] else "NULL"

                print(f"""INSERT INTO promo_codes (id, code, discount_type, discount_value, max_uses, uses_count, valid_from, valid_until, tariff_id, is_active, created_at, updated_at)
VALUES (
    '{promo[0]}',
    '{promo[1]}',
    '{promo[2]}',
    {promo[3]},
    {promo[4]},
    {promo[5]},
    '{promo[6]}',
    {valid_until_sql},
    '{promo[8]}',
    {promo[9]},
    '{promo[10]}',
    '{promo[11]}'
);""")
            else:
                print("ERROR: FRIENDLY promo code not found!")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(export_trial_data())
