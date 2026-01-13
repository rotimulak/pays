"""Script to create trial tariff and promo codes."""

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from src.core.config import settings
from src.db.models.promo_code import DiscountType, PromoCode
from src.db.models.tariff import PeriodUnit, Tariff
from src.db.session import get_session


async def main():
    """Create trial tariff and promo codes."""
    async with get_session() as session:
        # 1. Check if trial tariff already exists
        result = await session.execute(
            select(Tariff).where(Tariff.slug == "trial-30-7")
        )
        existing_tariff = result.scalar_one_or_none()

        if existing_tariff:
            print(f"[OK] Trial tariff already exists: {existing_tariff.id}")
            tariff = existing_tariff
        else:
            # Create trial tariff
            tariff = Tariff(
                id=uuid.uuid4(),
                slug="trial-30-7",
                name="Пробный тариф",
                description="Пробный период для новых пользователей: 30 токенов + 8 дней подписки",
                price=Decimal("0.01"),  # Minimum non-zero price to satisfy constraint
                tokens=30,
                subscription_days=0,  # Legacy field
                period_unit=PeriodUnit.DAY,
                period_value=8,
                subscription_fee=0,
                min_payment=Decimal("0.01"),
                is_active=False,  # Not shown in tariff list
                sort_order=999,
            )
            session.add(tariff)
            await session.flush()
            print(f"[OK] Created trial tariff: {tariff.id}")

        # 2. Create promo codes
        promo_codes_data = [
            {"code": "TRIAL2025", "max_uses": 100},
            {"code": "WELCOME100", "max_uses": 50},
            {"code": "FRIENDLY", "max_uses": 100},  # User requested
            {"code": "TESTCODE", "max_uses": 10},  # For testing
        ]

        for promo_data in promo_codes_data:
            # Check if exists
            result = await session.execute(
                select(PromoCode).where(PromoCode.code == promo_data["code"])
            )
            existing_promo = result.scalar_one_or_none()

            if existing_promo:
                print(f"[SKIP] Promo code already exists: {promo_data['code']}")
            else:
                promo = PromoCode(
                    id=uuid.uuid4(),
                    code=promo_data["code"],
                    discount_type=DiscountType.BONUS_TOKENS,
                    discount_value=Decimal("1"),  # Minimum positive value (not actually used for trial activation)
                    max_uses=promo_data["max_uses"],
                    uses_count=0,
                    valid_from=datetime.utcnow(),
                    valid_until=None,  # No expiry
                    tariff_id=tariff.id,
                    is_active=True,
                )
                session.add(promo)
                print(f"[OK] Created promo code: {promo_data['code']} (max {promo_data['max_uses']} uses)")

        await session.commit()
        print("\n[SUCCESS] Trial tariff setup complete!")
        print(f"Tariff ID: {tariff.id}")
        print(f"Slug: {tariff.slug}")
        print(f"Tokens: {tariff.tokens}")
        print(f"Period: {tariff.period_value} {tariff.period_unit.value}")


if __name__ == "__main__":
    asyncio.run(main())
