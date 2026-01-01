from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, OptimisticLockError
from src.db.models.user import User


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing or create new user.

        Uses INSERT ... ON CONFLICT DO NOTHING for atomic upsert.

        Returns:
            Tuple of (user, created) where created is True if new user was created.
        """
        # Try to insert, ignore if exists
        stmt = (
            insert(User)
            .values(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(User)
        )

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is not None:
            # New user was created
            return user, True

        # User already exists, fetch it
        existing = await self.get_by_id(user_id)
        if existing is None:
            # Should not happen in normal flow
            raise NotFoundError(
                message=f"User {user_id} not found after upsert",
                details={"user_id": user_id},
            )
        return existing, False

    async def update_balance(
        self,
        user_id: int,
        delta: int,
        expected_version: int,
    ) -> User:
        """Update token balance with optimistic locking.

        Args:
            user_id: User's Telegram ID
            delta: Amount to add (positive) or subtract (negative)
            expected_version: Expected balance_version for optimistic locking

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
            OptimisticLockError: If version mismatch (concurrent modification)
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .where(User.balance_version == expected_version)
            .values(
                token_balance=User.token_balance + delta,
                balance_version=User.balance_version + 1,
                updated_at=datetime.utcnow(),
            )
            .returning(User)
        )

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            # Check if user exists at all
            existing = await self.get_by_id(user_id)
            if existing is None:
                raise NotFoundError(
                    message=f"User {user_id} not found",
                    details={"user_id": user_id},
                )
            # User exists but version mismatch
            raise OptimisticLockError(
                message="Balance was modified by another operation",
                details={
                    "user_id": user_id,
                    "expected_version": expected_version,
                    "current_version": existing.balance_version,
                },
            )

        return user

    async def update_subscription(
        self,
        user_id: int,
        end_date: datetime,
    ) -> User:
        """Update subscription end date.

        Args:
            user_id: User's Telegram ID
            end_date: New subscription end date

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                subscription_end=end_date,
                updated_at=datetime.utcnow(),
            )
            .returning(User)
        )

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundError(
                message=f"User {user_id} not found",
                details={"user_id": user_id},
            )

        return user

    async def update(self, user: User) -> User:
        """Update user fields.

        Args:
            user: User object with updated fields

        Returns:
            Updated user
        """
        user.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(user)
        return user
