"""Invoice service for business logic."""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, ValidationError
from src.db.models.invoice import Invoice, InvoiceStatus
from src.db.repositories.invoice_repository import InvoiceRepository
from src.db.repositories.tariff_repository import TariffRepository
from src.services.dto.invoice import InvoiceDTO

# Invoice expires after 24 hours
INVOICE_EXPIRY_HOURS = 24

# Idempotency window: 1 hour
IDEMPOTENCY_WINDOW_MINUTES = 60


class InvoiceService:
    """Service for invoice-related operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.tariff_repo = TariffRepository(session)

    async def create_invoice(
        self,
        user_id: int,
        tariff_id: UUID,
        promo_code: str | None = None,
    ) -> Invoice:
        """Create invoice for tariff purchase.

        1. Check for existing pending invoice (idempotency)
        2. Get tariff details
        3. Apply promo code if provided (placeholder for M7)
        4. Calculate final amount
        5. Generate inv_id for Robokassa
        6. Create invoice with status=pending
        7. Set expires_at

        Args:
            user_id: Telegram user ID
            tariff_id: Tariff UUID
            promo_code: Optional promo code (not implemented, placeholder)

        Returns:
            Created invoice

        Raises:
            NotFoundError: If tariff not found
            ValidationError: If tariff is inactive
        """
        # Generate idempotency key
        idempotency_key = self.generate_idempotency_key(user_id, tariff_id)

        # Check for existing invoice with same idempotency key
        existing = await self.invoice_repo.get_by_idempotency_key(idempotency_key)
        if existing and existing.status == InvoiceStatus.PENDING:
            return existing

        # Get tariff
        tariff = await self.tariff_repo.get_by_id(tariff_id)
        if tariff is None:
            raise NotFoundError(
                message="Tariff not found",
                details={"tariff_id": str(tariff_id)},
            )

        if not tariff.is_active:
            raise ValidationError(
                message="Tariff is not available",
                details={"tariff_id": str(tariff_id)},
            )

        # Calculate amounts (promo code placeholder for M7)
        original_amount = tariff.price
        amount = original_amount  # No discount yet

        # Generate sequential inv_id for Robokassa
        inv_id = await self.invoice_repo.get_next_inv_id()

        # Create invoice
        now = datetime.utcnow()
        invoice = Invoice(
            id=uuid4(),
            inv_id=inv_id,
            user_id=user_id,
            tariff_id=tariff_id,
            promo_code_id=None,  # Placeholder for M7
            amount=amount,
            original_amount=original_amount,
            tokens=tariff.tokens,
            subscription_days=tariff.subscription_days,
            status=InvoiceStatus.PENDING,
            idempotency_key=idempotency_key,
            payment_url=None,  # Will be set when payment is initiated
            expires_at=now + timedelta(hours=INVOICE_EXPIRY_HOURS),
        )

        return await self.invoice_repo.create(invoice)

    async def get_or_create_invoice(
        self,
        user_id: int,
        tariff_id: UUID,
        idempotency_key: str | None = None,
    ) -> tuple[Invoice, bool]:
        """Get existing pending invoice or create new.

        Args:
            user_id: Telegram user ID
            tariff_id: Tariff UUID
            idempotency_key: Optional custom idempotency key

        Returns:
            Tuple of (invoice, created) where created is True if new.
        """
        # Use custom key or generate one
        key = idempotency_key or self.generate_idempotency_key(user_id, tariff_id)

        # Check for existing pending invoice
        existing = await self.invoice_repo.get_by_idempotency_key(key)
        if existing and existing.status == InvoiceStatus.PENDING:
            # Check if not expired
            if existing.expires_at > datetime.utcnow():
                return existing, False

        # Also check for any pending invoice for this user/tariff
        pending = await self.invoice_repo.get_pending_by_user(user_id, tariff_id)
        if pending:
            return pending, False

        # Create new invoice
        invoice = await self.create_invoice(user_id, tariff_id)
        return invoice, True

    async def get_user_invoices(
        self,
        user_id: int,
        limit: int = 20,
    ) -> list[InvoiceDTO]:
        """Get user's invoices for display."""
        invoices = await self.invoice_repo.get_user_invoices(user_id, limit=limit)
        return [await self._to_dto(inv) for inv in invoices]

    async def get_invoice_for_payment(self, invoice_id: UUID) -> InvoiceDTO | None:
        """Get invoice with all details for payment page."""
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            return None
        return await self._to_dto(invoice)

    async def cancel_invoice(self, invoice_id: UUID) -> Invoice:
        """Cancel pending invoice.

        Args:
            invoice_id: Invoice UUID

        Returns:
            Cancelled invoice

        Raises:
            NotFoundError: If invoice not found
            ValidationError: If invoice is not pending
        """
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            raise NotFoundError(
                message="Invoice not found",
                details={"invoice_id": str(invoice_id)},
            )

        if invoice.status != InvoiceStatus.PENDING:
            raise ValidationError(
                message="Only pending invoices can be cancelled",
                details={
                    "invoice_id": str(invoice_id),
                    "current_status": invoice.status.value,
                },
            )

        return await self.invoice_repo.update_status(
            invoice_id,
            InvoiceStatus.CANCELLED,
        )

    def generate_idempotency_key(
        self,
        user_id: int,
        tariff_id: UUID,
    ) -> str:
        """Generate idempotency key based on user, tariff, and time window.

        Key format: {user_id}:{tariff_id}:{time_window_hash}

        Time window is rounded to IDEMPOTENCY_WINDOW_MINUTES.
        """
        now = datetime.utcnow()
        # Round to window
        window = now.replace(second=0, microsecond=0)
        window_minutes = window.minute // IDEMPOTENCY_WINDOW_MINUTES * IDEMPOTENCY_WINDOW_MINUTES
        window = window.replace(minute=window_minutes)

        # Create hash
        data = f"{user_id}:{tariff_id}:{window.isoformat()}"
        key_hash = hashlib.sha256(data.encode()).hexdigest()[:16]

        return f"{user_id}:{tariff_id}:{key_hash}"

    async def _to_dto(self, invoice: Invoice) -> InvoiceDTO:
        """Convert Invoice model to DTO."""
        # Get tariff name
        tariff = await self.tariff_repo.get_by_id(invoice.tariff_id)
        tariff_name = tariff.name if tariff else "Неизвестный тариф"

        return InvoiceDTO(
            id=invoice.id,
            inv_id=invoice.inv_id,
            amount=invoice.amount,
            original_amount=invoice.original_amount,
            tokens=invoice.tokens,
            subscription_days=invoice.subscription_days,
            status=invoice.status,
            tariff_name=tariff_name,
            created_at=invoice.created_at,
            expires_at=invoice.expires_at,
        )

    def format_invoice_for_display(self, invoice: InvoiceDTO) -> str:
        """Format invoice for Telegram message."""
        lines = [
            "📋 <b>Счёт на оплату</b>",
            "",
            f"Тариф: <b>{invoice.tariff_name}</b>",
            f"Сумма: <b>{invoice.amount_display}</b>",
        ]

        if invoice.discount:
            discount_str = f"{invoice.discount:.2f}".rstrip("0").rstrip(".")
            lines.append(f"Скидка: -{discount_str} ₽")

        lines.append("")
        lines.append("Вы получите:")

        if invoice.tokens > 0:
            lines.append(f"• {invoice.tokens} токенов")

        if invoice.subscription_days > 0:
            lines.append(f"• {invoice.subscription_days} дней подписки")

        # Format expiry date
        expires_str = invoice.expires_at.strftime("%d.%m.%Y %H:%M")
        lines.append("")
        lines.append(f"Счёт действителен до: {expires_str}")

        return "\n".join(lines)
