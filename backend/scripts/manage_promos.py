"""CLI for promo code management.

Usage:
    # Create percent discount
    python -m scripts.manage_promos create SALE20 --type percent --value 20

    # Create fixed discount
    python -m scripts.manage_promos create FIXED100 --type fixed --value 100

    # Create bonus tokens
    python -m scripts.manage_promos create BONUS50 --type bonus_tokens --value 50

    # With options
    python -m scripts.manage_promos create VIP --type percent --value 30 \
        --max-uses 100 \
        --valid-until 2024-12-31 \
        --tariff premium

    # List promos
    python -m scripts.manage_promos list
    python -m scripts.manage_promos list --active

    # Show promo details
    python -m scripts.manage_promos show SALE20

    # Deactivate promo
    python -m scripts.manage_promos deactivate SALE20
"""

import argparse
import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db.session import async_session_factory  # noqa: E402
from db.models.promo_code import DiscountType, PromoCode  # noqa: E402
from db.repositories.promo_code_repository import PromoCodeRepository  # noqa: E402
from db.repositories.tariff_repository import TariffRepository  # noqa: E402


async def create_promo(args: argparse.Namespace) -> None:
    """Create new promo code."""
    async with async_session_factory() as session:
        repo = PromoCodeRepository(session)

        # Check if exists
        existing = await repo.get_by_code(args.code)
        if existing:
            print(f"Error: Promo code '{args.code}' already exists")
            return

        # Get tariff if specified
        tariff_id = None
        if args.tariff:
            tariff_repo = TariffRepository(session)
            tariff = await tariff_repo.get_by_slug(args.tariff)
            if not tariff:
                print(f"Error: Tariff '{args.tariff}' not found")
                return
            tariff_id = tariff.id

        # Parse dates
        valid_from = datetime.utcnow()
        if args.valid_from:
            valid_from = datetime.fromisoformat(args.valid_from)

        valid_until = None
        if args.valid_until:
            valid_until = datetime.fromisoformat(args.valid_until)

        # Create promo
        promo = PromoCode(
            id=uuid4(),
            code=args.code.upper(),
            discount_type=DiscountType(args.type),
            discount_value=Decimal(str(args.value)),
            max_uses=args.max_uses,
            uses_count=0,
            valid_from=valid_from,
            valid_until=valid_until,
            tariff_id=tariff_id,
            is_active=True,
        )

        await repo.create(promo)
        await session.commit()

        print(f"Created promo code: {promo.code}")
        print(f"  Type: {promo.discount_type.value}")
        print(f"  Value: {promo.discount_value}")
        if promo.max_uses:
            print(f"  Max uses: {promo.max_uses}")
        if promo.valid_until:
            print(f"  Valid until: {promo.valid_until}")
        if tariff_id:
            print(f"  Tariff: {args.tariff}")


async def list_promos(args: argparse.Namespace) -> None:
    """List promo codes."""
    async with async_session_factory() as session:
        repo = PromoCodeRepository(session)

        if args.active:
            promos = await repo.get_active()
        else:
            promos = await repo.get_all()

        if not promos:
            print("No promo codes found")
            return

        print(f"{'Code':<15} {'Type':<12} {'Value':<10} {'Uses':<12} {'Status':<10}")
        print("-" * 65)

        for p in promos:
            uses = f"{p.uses_count}/{p.max_uses}" if p.max_uses else str(p.uses_count)
            status = "Active" if p.is_active else "Inactive"
            print(
                f"{p.code:<15} {p.discount_type.value:<12} "
                f"{p.discount_value:<10} {uses:<12} {status:<10}"
            )


async def show_promo(args: argparse.Namespace) -> None:
    """Show promo code details."""
    async with async_session_factory() as session:
        repo = PromoCodeRepository(session)
        promo = await repo.get_by_code(args.code)

        if not promo:
            print(f"Error: Promo code '{args.code}' not found")
            return

        print(f"Code: {promo.code}")
        print(f"ID: {promo.id}")
        print(f"Type: {promo.discount_type.value}")
        print(f"Value: {promo.discount_value}")
        print(f"Uses: {promo.uses_count}/{promo.max_uses or 'unlimited'}")
        print(f"Active: {promo.is_active}")
        print(f"Valid from: {promo.valid_from}")
        print(f"Valid until: {promo.valid_until or 'N/A'}")
        print(f"Tariff: {promo.tariff_id or 'Any'}")
        print(f"Created: {promo.created_at}")


async def deactivate_promo(args: argparse.Namespace) -> None:
    """Deactivate promo code."""
    async with async_session_factory() as session:
        repo = PromoCodeRepository(session)
        promo = await repo.get_by_code(args.code)

        if not promo:
            print(f"Error: Promo code '{args.code}' not found")
            return

        if not promo.is_active:
            print(f"Promo code '{args.code}' is already inactive")
            return

        await repo.deactivate(promo.id)
        await session.commit()
        print(f"Deactivated promo code: {args.code}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Promo code management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create promo code")
    create_parser.add_argument("code", help="Promo code (will be uppercased)")
    create_parser.add_argument(
        "--type",
        "-t",
        required=True,
        choices=["percent", "fixed", "bonus_tokens"],
        help="Discount type",
    )
    create_parser.add_argument(
        "--value",
        "-v",
        type=float,
        required=True,
        help="Discount value (percent, rubles, or tokens)",
    )
    create_parser.add_argument(
        "--max-uses",
        "-m",
        type=int,
        help="Maximum uses limit",
    )
    create_parser.add_argument(
        "--valid-from",
        help="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
    )
    create_parser.add_argument(
        "--valid-until",
        help="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
    )
    create_parser.add_argument(
        "--tariff",
        help="Restrict to tariff slug",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List promo codes")
    list_parser.add_argument(
        "--active",
        "-a",
        action="store_true",
        help="Show only active promo codes",
    )

    # Show command
    show_parser = subparsers.add_parser("show", help="Show promo details")
    show_parser.add_argument("code", help="Promo code")

    # Deactivate command
    deact_parser = subparsers.add_parser("deactivate", help="Deactivate promo")
    deact_parser.add_argument("code", help="Promo code")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(create_promo(args))
    elif args.command == "list":
        asyncio.run(list_promos(args))
    elif args.command == "show":
        asyncio.run(show_promo(args))
    elif args.command == "deactivate":
        asyncio.run(deactivate_promo(args))


if __name__ == "__main__":
    main()
