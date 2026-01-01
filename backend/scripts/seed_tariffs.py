"""Seed database with test tariffs."""

import asyncio
import sys
from decimal import Decimal
from uuid import uuid4

from src.db.models.tariff import Tariff
from src.db.repositories.tariff_repository import TariffRepository
from src.db.session import async_session_factory

SEED_TARIFFS = [
    {
        "slug": "basic-200",
        "name": "Базовый 200",
        "description": "Тариф за 100 плюс 100 токенов",
        "price": Decimal("200.00"),
        "tokens": 100,
        "subscription_days": 30,
        "sort_order": 1,
        "is_active": True,
    },
]


async def seed_tariffs(force: bool = False) -> None:
    """Seed database with test tariffs.

    Args:
        force: If True, update tariffs even if they exist
    """
    async with async_session_factory() as session:
        repo = TariffRepository(session)

        for tariff_data in SEED_TARIFFS:
            existing = await repo.get_by_slug(tariff_data["slug"])

            if existing and not force:
                print(f"Tariff '{tariff_data['slug']}' already exists, skipping")
                continue

            if existing and force:
                # Update existing
                for key, value in tariff_data.items():
                    setattr(existing, key, value)
                await repo.update(existing)
                print(f"Updated tariff '{tariff_data['slug']}'")
            else:
                # Create new
                tariff = Tariff(id=uuid4(), **tariff_data)
                await repo.create(tariff)
                print(f"Created tariff '{tariff_data['slug']}'")

        await session.commit()

    print("\nSeeding complete!")


def main() -> None:
    """Entry point."""
    force = "--force" in sys.argv
    if force:
        print("Running with --force flag (will update existing tariffs)\n")

    asyncio.run(seed_tariffs(force=force))


if __name__ == "__main__":
    main()
