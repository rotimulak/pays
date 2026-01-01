"""Billing service for processing payments and crediting users."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.db.models.invoice import Invoice, InvoiceStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.invoice_repository import InvoiceRepository
from src.db.repositories.transaction_repository import TransactionRepository
from src.db.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class BillingService:
    """Service for processing payments and crediting users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.user_repo = UserRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self._audit_service: "AuditService | None" = None  # type: ignore[name-defined]
        self._notification_service: "NotificationService | None" = None  # type: ignore[name-defined]

    def set_audit_service(self, service: "AuditService") -> None:  # type: ignore[name-defined]
        """Set audit service for logging."""
        self._audit_service = service

    def set_notification_service(self, service: "NotificationService") -> None:  # type: ignore[name-defined]
        """Set notification service for sending messages."""
        self._notification_service = service

    async def process_successful_payment(self, invoice_id: UUID) -> Invoice:
        """Process successful payment.

        Steps:
        1. Get invoice with lock (FOR UPDATE)
        2. Check idempotency (status != pending -> return)
        3. Credit tokens if any
        4. Extend subscription if any
        5. Update invoice status to PAID
        6. Create audit log
        7. Send notification

        Args:
            invoice_id: UUID of paid invoice

        Returns:
            Updated invoice

        Raises:
            NotFoundError: Invoice not found
        """
        # 1. Get invoice with lock
        invoice = await self.invoice_repo.get_for_update(invoice_id)

        if not invoice:
            raise NotFoundError(
                message=f"Invoice {invoice_id} not found",
                details={"invoice_id": str(invoice_id)},
            )

        # 2. Idempotency check
        if invoice.status != InvoiceStatus.PENDING:
            logger.info(
                "Invoice %s already processed, status=%s",
                invoice_id,
                invoice.status.value,
            )
            return invoice

        # Get user for balance operations
        user = await self.user_repo.get_by_id(invoice.user_id)
        if not user:
            raise NotFoundError(
                message=f"User {invoice.user_id} not found",
                details={"user_id": invoice.user_id},
            )

        old_balance = user.token_balance
        old_subscription = user.subscription_end

        # 3. Credit tokens
        if invoice.tokens > 0:
            await self._credit_tokens(
                user_id=invoice.user_id,
                amount=invoice.tokens,
                invoice_id=invoice.id,
            )
            # Refresh user after balance update
            user = await self.user_repo.get_by_id(invoice.user_id)

        # 4. Extend subscription
        new_subscription = old_subscription
        if invoice.subscription_days > 0:
            new_subscription = await self._extend_subscription(
                user_id=invoice.user_id,
                days=invoice.subscription_days,
                invoice_id=invoice.id,
            )
            # Refresh user after subscription update
            user = await self.user_repo.get_by_id(invoice.user_id)

        # 5. Update invoice status
        invoice = await self.invoice_repo.update_status(
            invoice_id=invoice.id,
            status=InvoiceStatus.PAID,
            paid_at=datetime.utcnow(),
        )

        # 6. Audit log
        if self._audit_service:
            await self._audit_service.log_payment_processed(
                user_id=invoice.user_id,
                invoice_id=invoice.id,
                old_balance=old_balance,
                new_balance=user.token_balance if user else old_balance,
                old_subscription=old_subscription,
                new_subscription=new_subscription,
            )

        # 7. Notification
        if self._notification_service:
            await self._notification_service.notify_payment_success(
                user_id=invoice.user_id,
                invoice=invoice,
            )

        logger.info(
            "Payment processed: invoice_id=%s, tokens=%d, days=%d",
            invoice_id,
            invoice.tokens,
            invoice.subscription_days,
        )

        return invoice

    async def _credit_tokens(
        self,
        user_id: int,
        amount: int,
        invoice_id: UUID,
    ) -> int:
        """Credit tokens to user balance.

        Uses optimistic locking via balance_version to prevent
        concurrent update issues.

        Args:
            user_id: Telegram user ID
            amount: Number of tokens to add
            invoice_id: Associated invoice ID

        Returns:
            New balance after update
        """
        # Get current user state
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                message=f"User {user_id} not found",
                details={"user_id": user_id},
            )

        # Update balance with optimistic locking
        updated_user = await self.user_repo.update_balance(
            user_id=user_id,
            delta=amount,
            expected_version=user.balance_version,
        )

        new_balance = updated_user.token_balance

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.TOPUP,
            tokens_delta=amount,
            balance_after=new_balance,
            description="Пополнение баланса",
            invoice_id=invoice_id,
        )
        await self.transaction_repo.create(transaction)

        logger.info(
            "Tokens credited: user_id=%d, amount=%d, new_balance=%d",
            user_id,
            amount,
            new_balance,
        )

        return new_balance

    async def _extend_subscription(
        self,
        user_id: int,
        days: int,
        invoice_id: UUID,
    ) -> datetime:
        """Extend user subscription.

        If subscription is active, add days to current end date.
        If subscription expired or not set, start from now.

        Args:
            user_id: Telegram user ID
            days: Number of days to add
            invoice_id: Associated invoice ID

        Returns:
            New subscription end date
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                message=f"User {user_id} not found",
                details={"user_id": user_id},
            )

        now = datetime.utcnow()

        # Calculate new end date
        if user.subscription_end and user.subscription_end > now:
            # Extend from current end
            new_end = user.subscription_end + timedelta(days=days)
        else:
            # Start fresh from now
            new_end = now + timedelta(days=days)

        # Update subscription
        await self.user_repo.update_subscription(user_id, new_end)

        # Create transaction record (0 tokens, just for history)
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.TOPUP,
            tokens_delta=0,
            balance_after=user.token_balance,
            description=f"Подписка продлена на {days} дней",
            invoice_id=invoice_id,
            metadata_={"subscription_days": days, "new_end": new_end.isoformat()},
        )
        await self.transaction_repo.create(transaction)

        logger.info(
            "Subscription extended: user_id=%d, days=%d, new_end=%s",
            user_id,
            days,
            new_end,
        )

        return new_end
