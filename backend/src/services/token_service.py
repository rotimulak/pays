"""Token service for spending and balance operations."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    ConcurrentModificationError,
    InsufficientBalanceError,
    NotFoundError,
    OptimisticLockError,
    SubscriptionExpiredError,
    UserBlockedError,
)
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.transaction_repository import TransactionRepository
from src.db.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class TokenBalance:
    """Current token balance state."""

    user_id: int
    token_balance: int
    subscription_active: bool
    subscription_end: datetime | None
    can_spend: bool
    reason: str | None = None


@dataclass
class SpendResult:
    """Result of token spending."""

    transaction_id: UUID
    tokens_spent: int
    balance_before: int
    balance_after: int
    user_id: int


class TokenService:
    """Service for token operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.transaction_repo = TransactionRepository(session)

    async def check_balance(self, user_id: int) -> TokenBalance:
        """Check user's token balance and spending eligibility.

        Args:
            user_id: Telegram user ID

        Returns:
            TokenBalance with current state

        Raises:
            NotFoundError: User not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        now = datetime.utcnow()
        subscription_active = (
            user.subscription_end is not None and user.subscription_end > now
        )

        can_spend = True
        reason = None

        if user.is_blocked:
            can_spend = False
            reason = "User is blocked"
        elif not subscription_active:
            can_spend = False
            reason = "Subscription expired"
        elif user.token_balance <= 0:
            can_spend = False
            reason = "Insufficient balance"

        return TokenBalance(
            user_id=user.id,
            token_balance=user.token_balance,
            subscription_active=subscription_active,
            subscription_end=user.subscription_end,
            can_spend=can_spend,
            reason=reason,
        )

    async def can_spend(self, user_id: int, amount: int) -> tuple[bool, str | None]:
        """Check if user can spend specified amount.

        Args:
            user_id: Telegram user ID
            amount: Amount to spend

        Returns:
            (can_spend, reason)
        """
        balance = await self.check_balance(user_id)

        if not balance.can_spend:
            return False, balance.reason

        if balance.token_balance < amount:
            return False, f"Insufficient balance (need {amount}, have {balance.token_balance})"

        return True, None

    async def spend_tokens(
        self,
        user_id: int,
        amount: int,
        description: str,
        idempotency_key: str | None = None,
        metadata: dict | None = None,
    ) -> SpendResult:
        """Spend tokens from user's balance.

        Args:
            user_id: Telegram user ID
            amount: Amount to spend (positive)
            description: Description for transaction
            idempotency_key: Optional key for idempotency
            metadata: Optional additional data

        Returns:
            SpendResult with transaction details

        Raises:
            ValueError: Amount not positive
            NotFoundError: User not found
            UserBlockedError: User is blocked
            SubscriptionExpiredError: No active subscription
            InsufficientBalanceError: Not enough tokens
            ConcurrentModificationError: Race condition detected
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Check idempotency first
        if idempotency_key:
            existing = await self.transaction_repo.get_by_idempotency(idempotency_key)
            if existing:
                logger.info(
                    "Returning existing transaction: %s (idempotency_key=%s)",
                    existing.id,
                    idempotency_key,
                )
                return SpendResult(
                    transaction_id=existing.id,
                    tokens_spent=-existing.tokens_delta,
                    balance_before=existing.balance_after - existing.tokens_delta,
                    balance_after=existing.balance_after,
                    user_id=user_id,
                )

        # Get user with current version for optimistic locking
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Check blocked status
        if user.is_blocked:
            raise UserBlockedError(f"User {user_id} is blocked")

        # Check subscription
        now = datetime.utcnow()
        if not user.subscription_end or user.subscription_end <= now:
            raise SubscriptionExpiredError(
                f"Subscription expired on {user.subscription_end}"
                if user.subscription_end
                else "No subscription"
            )

        # Check balance
        if user.token_balance < amount:
            raise InsufficientBalanceError(
                required=amount,
                available=user.token_balance,
            )

        balance_before = user.token_balance
        new_balance = balance_before - amount

        # Update balance with optimistic locking
        try:
            await self.user_repo.update_balance(
                user_id=user_id,
                delta=-amount,
                expected_version=user.balance_version,
            )
        except OptimisticLockError:
            raise ConcurrentModificationError(
                "Balance was modified by another request. Please retry."
            )

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.SPEND,
            tokens_delta=-amount,
            balance_after=new_balance,
            description=description,
            idempotency_key=idempotency_key,
            metadata_=metadata or {},
        )
        await self.transaction_repo.create(transaction)

        logger.info(
            "Tokens spent: user=%d, amount=%d, balance=%d->%d, tx=%s",
            user_id,
            amount,
            balance_before,
            new_balance,
            transaction.id,
        )

        return SpendResult(
            transaction_id=transaction.id,
            tokens_spent=amount,
            balance_before=balance_before,
            balance_after=new_balance,
            user_id=user_id,
        )
