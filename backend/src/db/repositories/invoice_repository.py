"""Invoice repository for database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.db.models.invoice import Invoice, InvoiceStatus


class InvoiceRepository:
    """Repository for Invoice model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, invoice: Invoice) -> Invoice:
        """Create new invoice."""
        self.session.add(invoice)
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice

    async def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Get invoice by UUID."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_by_inv_id(self, inv_id: int) -> Invoice | None:
        """Get invoice by Robokassa InvId."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.inv_id == inv_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Invoice | None:
        """Get invoice by idempotency key."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_pending_by_user(
        self,
        user_id: int,
        tariff_id: UUID,
    ) -> Invoice | None:
        """Get pending invoice for user and tariff.

        Returns the most recent pending invoice if exists.
        """
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .where(Invoice.tariff_id == tariff_id)
            .where(Invoice.status == InvoiceStatus.PENDING)
            .where(Invoice.expires_at > datetime.utcnow())
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_user_invoices(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Invoice]:
        """Get user's invoices ordered by created_at desc."""
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        invoice_id: UUID,
        status: InvoiceStatus,
        paid_at: datetime | None = None,
    ) -> Invoice:
        """Update invoice status.

        Args:
            invoice_id: Invoice UUID
            status: New status
            paid_at: Payment completion time (for PAID status)

        Returns:
            Updated invoice

        Raises:
            NotFoundError: If invoice not found
        """
        values: dict[str, InvoiceStatus | datetime] = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if paid_at is not None:
            values["paid_at"] = paid_at

        stmt = (
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(**values)
            .returning(Invoice)
        )

        result = await self.session.execute(stmt)
        invoice = result.scalar_one_or_none()

        if invoice is None:
            raise NotFoundError(
                message=f"Invoice {invoice_id} not found",
                details={"invoice_id": str(invoice_id)},
            )

        return invoice

    async def get_for_update(self, invoice_id: UUID) -> Invoice | None:
        """Get invoice with FOR UPDATE lock.

        Use this when you need to update invoice atomically.
        """
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_next_inv_id(self) -> int:
        """Generate next sequential InvId for Robokassa.

        Uses MAX(inv_id) + 1 approach with a fallback to 1.
        Thread-safe due to transaction isolation.
        """
        result = await self.session.execute(
            select(func.coalesce(func.max(Invoice.inv_id), 0) + 1)
        )
        return int(result.scalar_one())

    async def expire_old_pending(self, before: datetime) -> int:
        """Set expired status for old pending invoices.

        Args:
            before: Expire invoices with expires_at before this time

        Returns:
            Number of expired invoices
        """
        stmt = (
            update(Invoice)
            .where(Invoice.status == InvoiceStatus.PENDING)
            .where(Invoice.expires_at < before)
            .values(
                status=InvoiceStatus.EXPIRED,
                updated_at=datetime.utcnow(),
            )
        )

        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_expiring_invoices(
        self,
        before: datetime,
        limit: int = 100,
    ) -> list[Invoice]:
        """Get pending invoices that will be expired.

        Useful for dry-run mode.

        Args:
            before: Get invoices with expires_at before this time
            limit: Maximum number of invoices to return

        Returns:
            List of invoices that would be expired
        """
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.status == InvoiceStatus.PENDING)
            .where(Invoice.expires_at < before)
            .limit(limit)
        )
        return list(result.scalars().all())
