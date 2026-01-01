"""Transaction repository for database operations."""

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.transaction import Transaction, TransactionType


class TransactionStats(BaseModel):
    """Aggregated transaction statistics."""

    total_topup: int
    total_spent: int
    total_refund: int
    transaction_count: int


class TransactionRepository:
    """Repository for Transaction model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, transaction: Transaction) -> Transaction:
        """Create new transaction."""
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)
        return transaction

    async def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Get transaction by ID."""
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        type_filter: TransactionType | None = None,
    ) -> list[Transaction]:
        """Get user's transactions with optional type filter.

        Args:
            user_id: User's Telegram ID
            limit: Maximum number of results
            offset: Number of results to skip
            type_filter: Filter by transaction type

        Returns:
            List of transactions ordered by created_at desc
        """
        query = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
        )

        if type_filter is not None:
            query = query.where(Transaction.type == type_filter)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_invoice(self, invoice_id: UUID) -> list[Transaction]:
        """Get transactions for specific invoice."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.invoice_id == invoice_id)
            .order_by(Transaction.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: int,
        type_filter: TransactionType | None = None,
    ) -> int:
        """Count user's transactions with optional type filter.

        Args:
            user_id: User's Telegram ID
            type_filter: Filter by transaction type

        Returns:
            Total count of transactions
        """
        query = select(func.count()).select_from(Transaction).where(
            Transaction.user_id == user_id
        )

        if type_filter is not None:
            query = query.where(Transaction.type == type_filter)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_user_stats(self, user_id: int) -> TransactionStats:
        """Get aggregated stats: total_topup, total_spent, etc.

        Uses SQL aggregation for efficiency.
        """
        # Get totals by type
        result = await self.session.execute(
            select(
                Transaction.type,
                func.sum(Transaction.tokens_delta).label("total"),
                func.count().label("count"),
            )
            .where(Transaction.user_id == user_id)
            .group_by(Transaction.type)
        )

        rows = result.all()

        # Initialize stats
        total_topup = 0
        total_spent = 0
        total_refund = 0
        transaction_count = 0

        for row in rows:
            tx_type, total, count = row
            transaction_count += count

            if tx_type == TransactionType.TOPUP:
                total_topup = abs(int(total or 0))
            elif tx_type == TransactionType.SPEND:
                total_spent = abs(int(total or 0))
            elif tx_type == TransactionType.REFUND:
                total_refund = abs(int(total or 0))
            # ADJUSTMENT is not included in stats

        return TransactionStats(
            total_topup=total_topup,
            total_spent=total_spent,
            total_refund=total_refund,
            transaction_count=transaction_count,
        )
