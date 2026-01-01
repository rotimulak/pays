"""
Script to expire old pending invoices.

Run periodically via cron or scheduler:
    python -m scripts.expire_invoices

Or with custom TTL:
    python -m scripts.expire_invoices --ttl-hours 12
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import settings
from src.db.repositories.invoice_repository import InvoiceRepository
from src.db.session import async_session_factory
from src.services.audit_service import AuditService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def expire_invoices(ttl_hours: int | None = None, dry_run: bool = False) -> int:
    """Expire old pending invoices.

    Args:
        ttl_hours: Hours after which pending invoice expires.
                   Defaults to INVOICE_TTL_HOURS from settings.
        dry_run: If True, show what would be expired without making changes.

    Returns:
        Number of expired invoices
    """
    ttl = ttl_hours or settings.invoice_ttl_hours
    cutoff_time = datetime.utcnow() - timedelta(hours=ttl)

    logger.info("Expiring invoices older than %s (TTL: %dh)", cutoff_time, ttl)

    async with async_session_factory() as session:
        repo = InvoiceRepository(session)

        if dry_run:
            # Just count what would be expired
            invoices = await repo.get_expiring_invoices(cutoff_time)
            expired_count = len(invoices)
            logger.info("DRY RUN: Would expire %d invoices", expired_count)
            for inv in invoices:
                logger.info(
                    "  - Invoice %s (user=%d, amount=%s, created=%s)",
                    inv.id,
                    inv.user_id,
                    inv.amount,
                    inv.created_at,
                )
            return expired_count

        # Actually expire invoices
        expired_count = await repo.expire_old_pending(cutoff_time)

        if expired_count > 0:
            audit = AuditService(session)
            await audit.log_invoices_expired(
                count=expired_count,
                cutoff_time=cutoff_time,
                ttl_hours=ttl,
            )

        await session.commit()

    logger.info("Expired %d invoices", expired_count)
    return expired_count


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Expire old pending invoices")
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=None,
        help=f"Hours until invoice expires (default: {settings.invoice_ttl_hours})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be expired without making changes",
    )

    args = parser.parse_args()

    count = await expire_invoices(
        ttl_hours=args.ttl_hours,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        print(f"Expired {count} invoices")


if __name__ == "__main__":
    asyncio.run(main())
