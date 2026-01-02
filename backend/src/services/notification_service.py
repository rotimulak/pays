"""Notification service for sending Telegram messages."""

import logging
from datetime import datetime

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
        new_balance: int | None = None,
    ) -> bool:
        """Send payment success notification.

        Args:
            user_id: Telegram user ID
            invoice: Paid invoice
            new_balance: Current token balance after payment

        Returns:
            True if message sent successfully
        """
        message = self._format_payment_success(invoice, new_balance)
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
            "⚠️ <b>Ваша подписка истекла</b>\n\n"
            "Чтобы продолжить пользоваться сервисом, "
            "оформите новую подписку: /tariffs\n\n"
            "Посмотреть детали: /subscription"
        )
        return await self._send_message(user_id, message)

    async def notify_renewal_success(
        self,
        user_id: int,
        new_end_date: datetime,
        tokens_spent: int,
        new_balance: int,
    ) -> bool:
        """Send auto-renewal success notification.

        Args:
            user_id: Telegram user ID
            new_end_date: New subscription end date
            tokens_spent: Tokens spent for renewal
            new_balance: Balance after renewal

        Returns:
            True if message sent successfully
        """
        formatted_date = new_end_date.strftime("%d.%m.%Y")
        message = (
            "✅ <b>Подписка автоматически продлена!</b>\n\n"
            f"📅 Новая дата окончания: {formatted_date}\n"
            f"💰 Списано токенов: {tokens_spent}\n"
            f"💳 Остаток на балансе: {new_balance}\n\n"
            "Управление подпиской: /subscription"
        )
        return await self._send_message(user_id, message)

    async def notify_renewal_failed(
        self,
        user_id: int,
        reason: str,
        required: int,
        available: int,
    ) -> bool:
        """Send auto-renewal failure notification.

        Args:
            user_id: Telegram user ID
            reason: Failure reason
            required: Required tokens
            available: Available tokens

        Returns:
            True if message sent successfully
        """
        if reason == "insufficient_balance":
            message = (
                "❌ <b>Не удалось продлить подписку</b>\n\n"
                f"Для продления требуется: {required} токенов\n"
                f"На вашем балансе: {available} токенов\n\n"
                "Пополните баланс: /tariffs\n"
                "Или отключите автопродление: /subscription"
            )
        else:
            message = (
                "❌ <b>Не удалось продлить подписку</b>\n\n"
                f"Причина: {reason}\n\n"
                "Обратитесь в поддержку или попробуйте позже."
            )
        return await self._send_message(user_id, message)

    async def notify_low_balance(
        self,
        user_id: int,
        current_balance: int,
        threshold: int,
    ) -> bool:
        """Send low balance warning.

        Args:
            user_id: Telegram user ID
            current_balance: Current token balance
            threshold: Threshold that triggered notification

        Returns:
            True if message sent successfully
        """
        if current_balance <= 5:
            urgency = "Kriticheski"
        elif current_balance <= 10:
            urgency = "Ochen"
        else:
            urgency = "Vnimanie"

        message = (
            f"{urgency} nizkij balans tokenov\n\n"
            f"Na vashem balanse ostalos: <b>{current_balance}</b> tokenov\n\n"
            "Popolnite balans, chtoby prodolzhit polzovatsya servisom.\n\n"
            "Popolnit: /tariffs"
        )
        return await self._send_message(user_id, message)

    def should_notify_low_balance(
        self,
        balance_after: int,
        last_notified: int | None,
        thresholds: list[int] | None = None,
    ) -> int | None:
        """Check if low balance notification should be sent.

        Args:
            balance_after: Balance after spending
            last_notified: Last threshold that was notified
            thresholds: Balance thresholds for notifications

        Returns:
            Threshold to notify at, or None if no notification needed
        """
        if thresholds is None:
            thresholds = [50, 20, 10, 5]

        # Sort descending
        thresholds = sorted(thresholds, reverse=True)

        for threshold in thresholds:
            # Balance crossed below threshold
            if balance_after <= threshold:
                # Haven't notified for this or lower threshold yet
                if last_notified is None or last_notified > threshold:
                    return threshold

        return None

    def _format_payment_success(self, invoice: Invoice, new_balance: int | None = None) -> str:
        """Format payment success message."""
        parts = ["Оплата успешно проведена!\n"]

        parts.append(f"Сумма: {invoice.amount} руб.\n")

        if invoice.tokens > 0:
            parts.append(f"Начислено токенов: {invoice.tokens}\n")

        if invoice.subscription_days > 0:
            parts.append(f"Подписка продлена на: {invoice.subscription_days} дней\n")

        if new_balance is not None:
            parts.append(f"\nТекущий баланс: {new_balance} токенов")

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
