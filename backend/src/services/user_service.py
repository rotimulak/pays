"""User service for business logic."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.services.dto.user import SubscriptionStatus, UserProfile


class UserService:
    """Service for user-related operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one.

        Also updates user info if changed.

        Returns:
            Tuple of (user, created) where created is True if new user was created.
        """
        user, created = await self.user_repo.get_or_create(
            user_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        if not created:
            # Update user info if changed
            needs_update = False
            if user.username != username:
                user.username = username
                needs_update = True
            if user.first_name != first_name:
                user.first_name = first_name
                needs_update = True
            if user.last_name != last_name:
                user.last_name = last_name
                needs_update = True

            if needs_update:
                await self.user_repo.update(user)

        return user, created

    async def get_user(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        return await self.user_repo.get_by_id(telegram_id)

    async def get_user_profile(self, telegram_id: int) -> UserProfile | None:
        """Get user profile with formatted data."""
        user = await self.user_repo.get_by_id(telegram_id)
        if user is None:
            return None

        status, status_text = self._format_subscription_status(user.subscription_end)

        return UserProfile(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            token_balance=user.token_balance,
            subscription_end=user.subscription_end,
            subscription_status=status,
            subscription_status_text=status_text,
        )

    def _format_subscription_status(
        self, subscription_end: datetime | None
    ) -> tuple[SubscriptionStatus, str]:
        """Format subscription status and text."""
        if subscription_end is None:
            return SubscriptionStatus.INACTIVE, "не активна"

        now = datetime.now(UTC)
        # Make subscription_end timezone-aware if it isn't
        if subscription_end.tzinfo is None:
            subscription_end = subscription_end.replace(tzinfo=UTC)

        if subscription_end < now:
            return SubscriptionStatus.EXPIRED, "истекла"

        # Check if expiring today
        if subscription_end.date() == now.date():
            return SubscriptionStatus.EXPIRING_TODAY, "истекает сегодня!"

        formatted_date = subscription_end.strftime("%d.%m.%Y")
        return SubscriptionStatus.ACTIVE, f"активна до {formatted_date}"
