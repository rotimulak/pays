"""Payment service for processing payments."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, PaymentError, ValidationError
from src.db.models.invoice import Invoice, InvoiceStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.invoice_repository import InvoiceRepository
from src.db.repositories.transaction_repository import TransactionRepository
from src.db.repositories.user_repository import UserRepository
from src.payments.providers import get_payment_provider
from src.payments.schemas import WebhookData

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment processing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.user_repo = UserRepository(session)

    async def create_payment_url(self, invoice_id: UUID) -> str:
        """Get payment URL for invoice.

        Args:
            invoice_id: Invoice UUID

        Returns:
            Payment URL

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
                message="Invoice is not available for payment",
                details={
                    "invoice_id": str(invoice_id),
                    "status": invoice.status.value,
                },
            )

        # Check if expired
        if invoice.expires_at < datetime.utcnow():
            raise ValidationError(
                message="Invoice has expired",
                details={"invoice_id": str(invoice_id)},
            )

        # Generate payment URL
        provider = get_payment_provider()
        payment_url = provider.generate_payment_url(invoice)

        # Save payment URL to invoice
        invoice.payment_url = payment_url
        await self.session.flush()

        return payment_url

    async def process_webhook(self, data: WebhookData) -> Invoice:
        """Process payment webhook callback.

        1. Find invoice by shp_invoice_id
        2. Check idempotency (status != pending → ignore)
        3. Update invoice status to PAID
        4. Credit tokens to user
        5. Update subscription if applicable
        6. Create transaction record

        Args:
            data: Parsed webhook data

        Returns:
            Updated invoice

        Raises:
            NotFoundError: If invoice not found
            PaymentError: If payment processing fails
        """
        # Find invoice
        invoice = await self.invoice_repo.get_by_id(data.shp_invoice_id)
        if invoice is None:
            raise NotFoundError(
                message="Invoice not found",
                details={"invoice_id": str(data.shp_invoice_id)},
            )

        # Idempotency check - if already processed, return
        if invoice.status != InvoiceStatus.PENDING:
            logger.info(
                "Invoice already processed: id=%s, status=%s",
                invoice.id,
                invoice.status.value,
            )
            return invoice

        # Verify invoice data matches
        if invoice.inv_id != data.inv_id:
            raise PaymentError(
                message="Invoice ID mismatch",
                details={
                    "expected": invoice.inv_id,
                    "received": data.inv_id,
                },
            )

        # Get invoice with lock to prevent race conditions
        invoice = await self.invoice_repo.get_for_update(invoice.id)
        if invoice is None or invoice.status != InvoiceStatus.PENDING:
            logger.info("Invoice changed during processing, skipping")
            return invoice  # type: ignore[return-value]

        # Get user
        user = await self.user_repo.get_by_id(invoice.user_id)
        if user is None:
            raise PaymentError(
                message="User not found",
                details={"user_id": invoice.user_id},
            )

        # Update invoice status
        now = datetime.utcnow()
        invoice = await self.invoice_repo.update_status(
            invoice_id=invoice.id,
            status=InvoiceStatus.PAID,
            paid_at=now,
        )

        # Credit tokens to user
        if invoice.tokens > 0:
            user = await self.user_repo.update_balance(
                user_id=user.id,
                delta=invoice.tokens,
                expected_version=user.balance_version,
            )

            # Create transaction record
            transaction = Transaction(
                user_id=user.id,
                type=TransactionType.TOPUP,
                tokens_delta=invoice.tokens,
                balance_after=user.token_balance,
                description=f"Оплата счёта #{invoice.inv_id}",
                invoice_id=invoice.id,
            )
            await self.transaction_repo.create(transaction)

        # Update subscription if applicable
        if invoice.subscription_days > 0:
            from datetime import timedelta

            # Calculate new end date
            current_end = user.subscription_end
            if current_end is None or current_end < now:
                new_end = now + timedelta(days=invoice.subscription_days)
            else:
                new_end = current_end + timedelta(days=invoice.subscription_days)

            await self.user_repo.update_subscription(user.id, new_end)

        logger.info(
            "Payment completed: invoice=%s, user=%d, tokens=%d, days=%d",
            invoice.id,
            user.id,
            invoice.tokens,
            invoice.subscription_days,
        )

        return invoice
