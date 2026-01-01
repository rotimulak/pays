"""Notification service for sending Telegram messages."""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.db.models.invoice import Invoice

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending Telegram notifications."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def notify_payment_success(
        self,
        user_id: int,
        invoice: Invoice,
    ) -> bool:
        """Send payment success notification.

        Args:
            user_id: Telegram user ID
            invoice: Paid invoice

        Returns:
            True if message sent successfully
        """
        message = self._format_payment_success(invoice)
        return await self._send_message(user_id, message)

    async def notify_subscription_expiring(
        self,
        user_id: int,
        days_left: int,
    ) -> bool:
        """Send subscription expiring warning.

        Args:
            user_id: Telegram user ID
            days_left: Days until subscription expires

        Returns:
            True if message sent successfully
        """
        if days_left == 0:
            message = (
                "Ваша подписка истекает сегодня!\n\n"
                "Продлите подписку, чтобы не потерять доступ к функциям.\n\n"
                "Выберите тариф: /tariffs"
            )
        elif days_left == 1:
            message = (
                "Ваша подписка истекает завтра!\n\n"
                "Продлите подписку: /tariffs"
            )
        else:
            message = (
                f"Ваша подписка истекает через {days_left} дней.\n\n"
                "Продлите подписку: /tariffs"
            )

        return await self._send_message(user_id, message)

    async def notify_subscription_expired(self, user_id: int) -> bool:
        """Send subscription expired notification."""
        message = (
            "Ваша подписка истекла.\n\n"
            "Чтобы продолжить пользоваться сервисом, "
            "оформите новую подписку: /tariffs"
        )
        return await self._send_message(user_id, message)

    async def notify_low_balance(
        self,
        user_id: int,
        current_balance: int,
        threshold: int,
    ) -> bool:
        """Send low balance warning."""
        message = (
            f"На вашем балансе осталось мало токенов: {current_balance}\n\n"
            "Пополните баланс, чтобы продолжить пользоваться сервисом.\n\n"
            "Выберите тариф: /tariffs"
        )
        return await self._send_message(user_id, message)

    def _format_payment_success(self, invoice: Invoice) -> str:
        """Format payment success message."""
        parts = ["Оплата успешно проведена!\n"]

        parts.append(f"Сумма: {invoice.amount} руб.\n")

        if invoice.tokens > 0:
            parts.append(f"Начислено токенов: {invoice.tokens}\n")

        if invoice.subscription_days > 0:
            parts.append(f"Подписка продлена на: {invoice.subscription_days} дней\n")

        parts.append("\nСпасибо за покупку!")

        return "".join(parts)

    async def _send_message(
        self,
        user_id: int,
        text: str,
        reply_markup=None,
    ) -> bool:
        """Send message to user with error handling.

        Returns:
            True if message sent, False if user blocked bot or error
        """
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
            )
            logger.info("Notification sent to user %d", user_id)
            return True

        except TelegramForbiddenError:
            logger.warning("User %d blocked the bot", user_id)
            return False

        except TelegramBadRequest as e:
            logger.error("Failed to send notification to %d: %s", user_id, e)
            return False

        except Exception as e:
            logger.error("Unexpected error sending to %d: %s", user_id, e)
            return False
