"""Transaction service for transaction operations."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.transaction_repository import TransactionRepository, TransactionStats
from src.services.dto.transaction import TransactionDTO, TransactionListDTO

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for transaction operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transaction_repo = TransactionRepository(session)

    async def create_transaction(
        self,
        user_id: int,
        type: TransactionType,
        tokens_delta: int,
        balance_after: int,
        description: str | None = None,
        invoice_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> Transaction:
        """Create new transaction record.

        Args:
            user_id: Telegram user ID
            type: Transaction type (topup, spend, refund, adjustment)
            tokens_delta: Change in tokens (positive or negative)
            balance_after: Balance after this transaction
            description: Human-readable description
            invoice_id: Related invoice if any
            metadata: Additional data as JSON

        Returns:
            Created transaction
        """
        transaction = Transaction(
            user_id=user_id,
            type=type,
            tokens_delta=tokens_delta,
            balance_after=balance_after,
            description=description,
            invoice_id=invoice_id,
            metadata_=metadata or {},
        )

        return await self.transaction_repo.create(transaction)

    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        type_filter: TransactionType | None = None,
    ) -> TransactionListDTO:
        """Get user transactions with pagination.

        Args:
            user_id: Telegram user ID
            limit: Max number of transactions
            offset: Skip first N transactions
            type_filter: Filter by transaction type

        Returns:
            TransactionListDTO with items and pagination info
        """
        transactions = await self.transaction_repo.get_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            type_filter=type_filter,
        )

        total = await self.transaction_repo.count_by_user(user_id, type_filter)

        items = [self._to_dto(t) for t in transactions]

        return TransactionListDTO(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    async def get_user_stats(self, user_id: int) -> TransactionStats:
        """Get aggregated transaction stats."""
        return await self.transaction_repo.get_user_stats(user_id)

    async def get_recent_spending(self, user_id: int, days: int = 7) -> int:
        """Get total spending for recent days.

        Args:
            user_id: Telegram user ID
            days: Number of days to look back

        Returns:
            Total tokens spent (absolute value)
        """
        return await self.transaction_repo.get_recent_spending(user_id, days)

    def _to_dto(self, transaction: Transaction) -> TransactionDTO:
        """Convert model to DTO."""
        return TransactionDTO(
            id=transaction.id,
            type=transaction.type,
            type_display=self._format_type(transaction.type),
            tokens_delta=transaction.tokens_delta,
            tokens_delta_display=self._format_delta(transaction.tokens_delta),
            balance_after=transaction.balance_after,
            description=transaction.description,
            invoice_id=transaction.invoice_id,
            created_at=transaction.created_at,
            created_at_display=transaction.created_at.strftime("%d.%m.%Y %H:%M"),
        )

    def _format_type(self, type: TransactionType) -> str:
        """Format transaction type for display."""
        mapping = {
            TransactionType.TOPUP: "Пополнение",
            TransactionType.SPEND: "Списание",
            TransactionType.REFUND: "Возврат",
            TransactionType.ADJUSTMENT: "Корректировка",
        }
        return mapping.get(type, str(type.value))

    def _format_delta(self, delta: float) -> str:
        """Format delta with sign."""
        delta_rounded = round(delta, 2)
        if delta > 0:
            return f"+{delta_rounded}"
        return str(delta_rounded)
