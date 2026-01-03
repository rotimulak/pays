"""Subscription management service.

M11: Updated to use tariff-based subscription fee and period.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models.tariff import Tariff
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User
from src.db.repositories.tariff_repository import TariffRepository
from src.db.repositories.transaction_repository import TransactionRepository
from src.db.repositories.user_repository import UserRepository
from src.services.billing_service import calculate_subscription_end
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing user subscriptions."""

    def __init__(
        self,
        session: AsyncSession,
        notification_service: NotificationService,
    ) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.tariff_repo = TariffRepository(session)
        self.notification_service = notification_service

    async def _get_tariff(self) -> Tariff | None:
        """Get default tariff for subscription operations."""
        return await self.tariff_repo.get_default_tariff()

    async def check_expiring_subscriptions(
        self,
        notify_days: list[int] | None = None,
    ) -> dict[int, list[int]]:
        """Check for expiring subscriptions and send notifications.

        M11: Now includes balance info and subscription_fee in notifications.

        Args:
            notify_days: Days before expiry to notify (default from settings)

        Returns:
            Dict mapping days_left to list of notified user IDs
        """
        if notify_days is None:
            notify_days = settings.subscription_notify_days

        # M11: Get tariff for subscription_fee info
        tariff = await self._get_tariff()
        subscription_fee = tariff.subscription_fee if tariff else settings.subscription_renewal_price

        notified: dict[int, list[int]] = {}
        now = datetime.utcnow()

        for days in sorted(notify_days, reverse=True):
            notified[days] = []
            users = await self.user_repo.get_expiring_subscriptions(days)

            for user in users:
                if user.subscription_end is None:
                    continue

                # Calculate actual days left
                days_left = (user.subscription_end - now).days

                # Skip if already notified for this threshold
                if (
                    user.last_subscription_notification is not None
                    and user.last_subscription_notification <= days_left
                ):
                    continue

                # Only notify if we're at or past this threshold
                if days_left <= days:
                    try:
                        # M11: Include balance and fee info
                        success = await self.notification_service.notify_subscription_expiring(
                            user.id,
                            days_left,
                            balance=user.token_balance,
                            subscription_fee=subscription_fee,
                        )
                        if success:
                            await self.user_repo.update_subscription_notification(
                                user.id,
                                days_left,
                            )
                            notified[days].append(user.id)
                            logger.info(
                                "Sent expiry notification to user %d (days_left=%d)",
                                user.id,
                                days_left,
                            )
                    except Exception as e:
                        logger.error(
                            "Failed to send expiry notification to user %d: %s",
                            user.id,
                            e,
                        )

        await self.session.commit()
        return notified

    async def process_auto_renewal(self, user_id: int) -> bool:
        """Attempt to auto-renew subscription for a user.

        M11: Uses tariff-based subscription_fee and period.

        Args:
            user_id: User's Telegram ID

        Returns:
            True if renewal successful, False otherwise
        """
        user = await self.user_repo.get_for_update(user_id)

        if user is None:
            logger.warning("User %d not found for auto-renewal", user_id)
            return False

        if not user.auto_renew:
            logger.debug("Auto-renew disabled for user %d", user_id)
            return False

        # M11: Get renewal price from tariff
        tariff = await self._get_tariff()
        if tariff is None:
            logger.error("No active tariff found for auto-renewal")
            return False

        renewal_price = tariff.subscription_fee

        if user.token_balance < renewal_price:
            logger.info(
                "User %d has insufficient balance for renewal (%d < %d)",
                user_id,
                user.token_balance,
                renewal_price,
            )
            await self.notification_service.notify_renewal_failed(
                user_id,
                reason="insufficient_balance",
                required=renewal_price,
                available=user.token_balance,
            )
            return False

        try:
            # Deduct tokens
            updated_user = await self.user_repo.update_balance(
                user_id,
                delta=-renewal_price,
                expected_version=user.balance_version,
            )

            # M11: Calculate new end date using tariff period
            new_end = calculate_subscription_end(
                current_end=user.subscription_end,
                unit=tariff.period_unit,
                value=tariff.period_value,
            )

            # Update subscription end date
            await self.user_repo.update_subscription(user_id, new_end)

            # Reset notification counter
            await self.user_repo.reset_subscription_notification(user_id)

            # Create transaction
            transaction = Transaction(
                user_id=user_id,
                type=TransactionType.SUBSCRIPTION,
                tokens_delta=-renewal_price,
                balance_after=updated_user.token_balance,
                description=f"Автопродление подписки ({tariff.period_value} {tariff.period_unit.value})",
            )
            await self.transaction_repo.create(transaction)

            await self.session.commit()

            # Send success notification
            await self.notification_service.notify_renewal_success(
                user_id,
                new_end,
                renewal_price,
                updated_user.token_balance,
            )

            logger.info(
                "Successfully renewed subscription for user %d until %s",
                user_id,
                new_end,
            )
            return True

        except Exception as e:
            logger.error("Failed to renew subscription for user %d: %s", user_id, e)
            await self.session.rollback()
            await self.notification_service.notify_renewal_failed(
                user_id,
                reason="system_error",
                required=renewal_price,
                available=user.token_balance,
            )
            return False

    async def process_all_auto_renewals(self) -> dict[str, list[int]]:
        """Process auto-renewal for all eligible users.

        Returns:
            Dict with 'success' and 'failed' user ID lists
        """
        users = await self.user_repo.get_users_for_auto_renewal()
        result: dict[str, list[int]] = {"success": [], "failed": []}

        for user in users:
            try:
                success = await self.process_auto_renewal(user.id)
                if success:
                    result["success"].append(user.id)
                else:
                    result["failed"].append(user.id)
            except Exception as e:
                logger.error(
                    "Error processing auto-renewal for user %d: %s",
                    user.id,
                    e,
                )
                result["failed"].append(user.id)

        logger.info(
            "Auto-renewal complete: %d success, %d failed",
            len(result["success"]),
            len(result["failed"]),
        )
        return result

    async def expire_subscriptions(self) -> list[int]:
        """Mark expired subscriptions and notify users.

        M11: Includes balance and fee info in notifications.

        Returns:
            List of user IDs whose subscriptions expired
        """
        # M11: Get tariff for fee info
        tariff = await self._get_tariff()
        subscription_fee = tariff.subscription_fee if tariff else settings.subscription_renewal_price

        users = await self.user_repo.get_expired_subscriptions()
        expired_users: list[int] = []

        for user in users:
            try:
                # M11: Notify with balance and fee info
                await self.notification_service.notify_subscription_expired(
                    user.id,
                    subscription_fee=subscription_fee,
                    balance=user.token_balance,
                )
                expired_users.append(user.id)
                logger.info("Subscription expired for user %d", user.id)
            except Exception as e:
                logger.error(
                    "Failed to process expiration for user %d: %s",
                    user.id,
                    e,
                )

        return expired_users

    async def get_subscription_status(self, user: User) -> dict:
        """Get detailed subscription status for a user.

        Args:
            user: User model

        Returns:
            Dict with subscription details
        """
        now = datetime.utcnow()

        if user.subscription_end is None:
            return {
                "status": "none",
                "status_text": "Нет активной подписки",
                "end_date": None,
                "days_left": None,
                "auto_renew": user.auto_renew,
                "renewal_price": settings.subscription_renewal_price,
                "can_auto_renew": user.token_balance >= settings.subscription_renewal_price,
            }

        if user.subscription_end <= now:
            return {
                "status": "expired",
                "status_text": "Подписка истекла",
                "end_date": user.subscription_end,
                "days_left": 0,
                "auto_renew": user.auto_renew,
                "renewal_price": settings.subscription_renewal_price,
                "can_auto_renew": user.token_balance >= settings.subscription_renewal_price,
            }

        days_left = (user.subscription_end - now).days

        if days_left <= 3:
            status_text = f"Подписка истекает через {days_left} дн."
        else:
            status_text = f"Активна до {user.subscription_end.strftime('%d.%m.%Y')}"

        return {
            "status": "active",
            "status_text": status_text,
            "end_date": user.subscription_end,
            "days_left": days_left,
            "auto_renew": user.auto_renew,
            "renewal_price": settings.subscription_renewal_price,
            "can_auto_renew": user.token_balance >= settings.subscription_renewal_price,
        }

    async def toggle_auto_renew(self, user_id: int) -> bool:
        """Toggle auto-renew setting for user.

        Args:
            user_id: User's Telegram ID

        Returns:
            New auto_renew value
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        new_value = not user.auto_renew
        await self.user_repo.update_auto_renew(user_id, new_value)
        await self.session.commit()

        logger.info(
            "User %d toggled auto_renew to %s",
            user_id,
            new_value,
        )
        return new_value

    async def manual_renew(self, user_id: int) -> bool:
        """Manually renew subscription (user-initiated).

        M11: Uses tariff-based subscription_fee and period.

        Args:
            user_id: User's Telegram ID

        Returns:
            True if renewal successful
        """
        user = await self.user_repo.get_for_update(user_id)

        if user is None:
            raise ValueError(f"User {user_id} not found")

        # M11: Get renewal price from tariff
        tariff = await self._get_tariff()
        if tariff is None:
            logger.error("No active tariff found for manual renewal")
            return False

        renewal_price = tariff.subscription_fee

        if user.token_balance < renewal_price:
            return False

        # Deduct tokens
        updated_user = await self.user_repo.update_balance(
            user_id,
            delta=-renewal_price,
            expected_version=user.balance_version,
        )

        # M11: Calculate new end date using tariff period
        new_end = calculate_subscription_end(
            current_end=user.subscription_end,
            unit=tariff.period_unit,
            value=tariff.period_value,
        )

        # Update subscription
        await self.user_repo.update_subscription(user_id, new_end)
        await self.user_repo.reset_subscription_notification(user_id)

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.SUBSCRIPTION,
            tokens_delta=-renewal_price,
            balance_after=updated_user.token_balance,
            description=f"Продление подписки ({tariff.period_value} {tariff.period_unit.value})",
        )
        await self.transaction_repo.create(transaction)

        await self.session.commit()

        logger.info(
            "User %d manually renewed subscription until %s",
            user_id,
            new_end,
        )
        return True
