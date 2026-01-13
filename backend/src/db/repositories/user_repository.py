from datetime import datetime, timedelta

from sqlalchemy import and_, select, update
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
        delta: float,
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

    async def update_last_balance_notification(
        self,
        user_id: int,
        threshold: int,
    ) -> None:
        """Update last balance notification threshold.

        Args:
            user_id: User's Telegram ID
            threshold: Balance threshold that was notified
        """
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_balance_notification=threshold,
                updated_at=datetime.utcnow(),
            )
        )

    async def reset_balance_notification(self, user_id: int) -> None:
        """Reset balance notification threshold after topup.

        Called after user tops up balance to enable future notifications.

        Args:
            user_id: User's Telegram ID
        """
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_balance_notification=None,
                updated_at=datetime.utcnow(),
            )
        )

    async def get_expiring_subscriptions(
        self,
        days_ahead: int,
    ) -> list[User]:
        """Get users with subscriptions expiring within N days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of users with expiring subscriptions
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead + 1)

        result = await self.session.execute(
            select(User).where(
                and_(
                    User.subscription_end.isnot(None),
                    User.subscription_end > now,
                    User.subscription_end <= cutoff,
                    User.is_blocked == False,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def get_expired_subscriptions(self) -> list[User]:
        """Get users with expired subscriptions (past end date).

        Returns:
            List of users with expired subscriptions
        """
        now = datetime.utcnow()

        result = await self.session.execute(
            select(User).where(
                and_(
                    User.subscription_end.isnot(None),
                    User.subscription_end <= now,
                    User.is_blocked == False,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def get_users_for_auto_renewal(self) -> list[User]:
        """Get users eligible for auto-renewal.

        Returns:
            Users with auto_renew=True and subscription expiring today or expired
        """
        now = datetime.utcnow()
        # Users whose subscription expires today or has already expired
        cutoff = now + timedelta(days=1)

        result = await self.session.execute(
            select(User).where(
                and_(
                    User.subscription_end.isnot(None),
                    User.subscription_end <= cutoff,
                    User.auto_renew == True,  # noqa: E712
                    User.is_blocked == False,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def update_auto_renew(self, user_id: int, enabled: bool) -> User:
        """Update auto-renew setting for user.

        Args:
            user_id: User's Telegram ID
            enabled: Whether auto-renew should be enabled

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                auto_renew=enabled,
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

    async def update_subscription_notification(
        self,
        user_id: int,
        days_before: int,
    ) -> None:
        """Update last subscription notification days.

        Args:
            user_id: User's Telegram ID
            days_before: Days before expiry when notification was sent
        """
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_subscription_notification=days_before,
                updated_at=datetime.utcnow(),
            )
        )

    async def reset_subscription_notification(self, user_id: int) -> None:
        """Reset subscription notification after renewal.

        Args:
            user_id: User's Telegram ID
        """
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_subscription_notification=None,
                updated_at=datetime.utcnow(),
            )
        )

    async def get_for_update(self, user_id: int) -> User | None:
        """Get user with row-level lock for atomic updates.

        Args:
            user_id: User's Telegram ID

        Returns:
            User with lock or None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        return result.scalar_one_or_none()
