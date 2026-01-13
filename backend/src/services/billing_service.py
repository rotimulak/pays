"""Billing service for processing payments and crediting users."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.db.models.invoice import Invoice, InvoiceStatus
from src.db.models.tariff import PeriodUnit, Tariff
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.invoice_repository import InvoiceRepository
from src.db.repositories.tariff_repository import TariffRepository
from src.db.repositories.transaction_repository import TransactionRepository
from src.db.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def calculate_subscription_end(
    current_end: datetime | None,
    unit: PeriodUnit,
    value: int,
) -> datetime:
    """Calculate next subscription end date.

    Args:
        current_end: Current subscription end (or None for new subscription)
        unit: Period unit (hour/day/month)
        value: Number of units

    Returns:
        New subscription end datetime
    """
    base = current_end if current_end and current_end > datetime.utcnow() else datetime.utcnow()

    if unit == PeriodUnit.HOUR:
        return base + timedelta(hours=value)
    elif unit == PeriodUnit.DAY:
        return base + timedelta(days=value)
    elif unit == PeriodUnit.MONTH:
        return base + relativedelta(months=value)
    else:
        raise ValueError(f"Unknown period unit: {unit}")


@dataclass
class PaymentResult:
    """Result of M11 payment processing."""

    tokens_credited: int
    subscription_fee_charged: int
    subscription_activated: bool
    subscription_end: datetime | None
    new_balance: int


class BillingService:
    """Service for processing payments and crediting users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.user_repo = UserRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.tariff_repo = TariffRepository(session)
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
                new_balance=user.token_balance if user else None,
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
        amount: float,
        invoice_id: UUID,
    ) -> float:
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

    # ========== M11: Simplified Payment UX ==========

    def is_subscription_active(self, user) -> bool:
        """Check if user's subscription is currently active.

        Args:
            user: User model instance

        Returns:
            True if subscription_end > now, False otherwise
        """
        if user.subscription_end is None:
            return False
        return user.subscription_end > datetime.utcnow()

    async def process_m11_payment(
        self,
        user_id: int,
        amount: Decimal,
        tariff: Tariff,
        invoice_id: UUID,
    ) -> PaymentResult:
        """Process payment with M11 simplified UX logic.

        M11 Logic:
        - If subscription is inactive: deduct subscription_fee, activate subscription
        - Remaining tokens go to balance
        - If subscription is active: all tokens go to balance

        Args:
            user_id: Telegram user ID
            amount: Payment amount in RUB
            tariff: Tariff with subscription settings
            invoice_id: Invoice UUID for transaction records

        Returns:
            PaymentResult with details of what happened
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                message=f"User {user_id} not found",
                details={"user_id": user_id},
            )

        # Convert rubles to tokens (1:1 ratio)
        total_tokens = int(amount)
        subscription_was_active = self.is_subscription_active(user)

        subscription_fee_charged = 0
        subscription_end: datetime | None = None
        subscription_activated = False

        if not subscription_was_active:
            # First payment or subscription expired - charge subscription fee
            subscription_fee_charged = tariff.subscription_fee
            tokens_to_credit = total_tokens - subscription_fee_charged

            # Activate subscription
            subscription_end = calculate_subscription_end(
                current_end=None,
                unit=tariff.period_unit,
                value=tariff.period_value,
            )
            await self.user_repo.update_subscription(user_id, subscription_end)
            subscription_activated = True

            logger.info(
                "M11: Subscription activated for user %d until %s (fee: %d tokens)",
                user_id,
                subscription_end,
                subscription_fee_charged,
            )
        else:
            # Subscription active - all tokens go to balance
            tokens_to_credit = total_tokens

        # Credit tokens to balance
        if tokens_to_credit > 0:
            updated_user = await self.user_repo.update_balance(
                user_id=user_id,
                delta=tokens_to_credit,
                expected_version=user.balance_version,
            )
            new_balance = updated_user.token_balance
        else:
            new_balance = user.token_balance

        # Create transaction record
        if subscription_activated:
            description = f"Пополнение {int(amount)}₽: {subscription_fee_charged} ток. абонплата + {tokens_to_credit} ток. баланс"
        else:
            description = f"Пополнение баланса на {tokens_to_credit} токенов"

        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.TOPUP,
            tokens_delta=tokens_to_credit,
            balance_after=new_balance,
            description=description,
            invoice_id=invoice_id,
            metadata_={
                "amount_rub": str(amount),
                "subscription_fee": subscription_fee_charged,
                "subscription_activated": subscription_activated,
            },
        )
        await self.transaction_repo.create(transaction)

        logger.info(
            "M11 payment processed: user=%d, amount=%s, tokens=%d, fee=%d, activated=%s",
            user_id,
            amount,
            tokens_to_credit,
            subscription_fee_charged,
            subscription_activated,
        )

        return PaymentResult(
            tokens_credited=tokens_to_credit,
            subscription_fee_charged=subscription_fee_charged,
            subscription_activated=subscription_activated,
            subscription_end=subscription_end,
            new_balance=new_balance,
        )
