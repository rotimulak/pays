"""Notification service for sending Telegram messages."""

import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from decimal import Decimal

from src.db.models.invoice import Invoice
from src.services.billing_service import PaymentResult

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

    async def notify_m11_payment_success(
        self,
        user_id: int,
        result: PaymentResult,
        amount: Decimal,
    ) -> bool:
        """Send M11 payment success notification.

        Shows subscription fee deduction and tokens credited separately.

        Args:
            user_id: Telegram user ID
            result: PaymentResult from billing service
            amount: Payment amount in RUB

        Returns:
            True if message sent successfully
        """
        message = self._format_m11_payment_success(result, amount)
        return await self._send_message(user_id, message)

    def _format_m11_payment_success(
        self,
        result: PaymentResult,
        amount: Decimal,
    ) -> str:
        """Format M11 payment success message."""
        parts = ["✅ <b>Оплата успешно проведена!</b>\n\n"]

        parts.append(f"💰 Сумма: {amount}₽\n")

        if result.subscription_activated:
            parts.append(f"📅 Абонплата: {result.subscription_fee_charged} токенов\n")
            parts.append(f"💳 На баланс: {result.tokens_credited} токенов\n")
            if result.subscription_end:
                formatted_date = result.subscription_end.strftime("%d.%m.%Y")
                parts.append(f"\n🎉 Подписка активирована до: {formatted_date}\n")
        else:
            parts.append(f"💳 Начислено токенов: {result.tokens_credited}\n")

        parts.append(f"\n📊 Текущий баланс: {result.new_balance} токенов")
        parts.append("\n\nСпасибо за покупку!")

        return "".join(parts)

    async def notify_subscription_expiring(
        self,
        user_id: int,
        days_left: int,
        balance: int | None = None,
        subscription_fee: int | None = None,
    ) -> bool:
        """Send subscription expiring warning.

        M11: Updated to show balance info and auto-renewal status.

        Args:
            user_id: Telegram user ID
            days_left: Days until subscription expires
            balance: Current token balance (optional)
            subscription_fee: Fee required for renewal (optional)

        Returns:
            True if message sent successfully
        """
        # M11: Show balance and renewal info
        balance_info = ""
        if balance is not None and subscription_fee is not None:
            if balance >= subscription_fee:
                balance_info = (
                    f"\n💳 Баланс: {balance} токенов\n"
                    f"✅ Достаточно для автопродления ({subscription_fee} токенов)"
                )
            else:
                balance_info = (
                    f"\n💳 Баланс: {balance} токенов\n"
                    f"⚠️ Недостаточно для автопродления (нужно {subscription_fee})"
                )

        if days_left == 0:
            message = (
                "⏰ <b>Подписка истекает сегодня!</b>\n"
                f"{balance_info}\n\n"
                "Пополните баланс: /balance"
            )
        elif days_left == 1:
            message = (
                "⏰ <b>Подписка истекает завтра!</b>\n"
                f"{balance_info}\n\n"
                "Пополните баланс: /balance"
            )
        else:
            message = (
                f"⏰ <b>Подписка истекает через {days_left} дн.</b>\n"
                f"{balance_info}\n\n"
                "Пополните баланс: /balance"
            )

        return await self._send_message(user_id, message)

    async def notify_subscription_expired(
        self,
        user_id: int,
        subscription_fee: int | None = None,
        balance: int | None = None,
    ) -> bool:
        """Send subscription expired notification.

        M11: Updated messaging to point to balance instead of tariffs.
        """
        balance_info = ""
        if balance is not None and subscription_fee is not None:
            balance_info = (
                f"\n💳 Баланс: {balance} токенов\n"
                f"Для продления нужно: {subscription_fee} токенов"
            )

        message = (
            "⚠️ <b>Подписка деактивирована</b>\n"
            f"{balance_info}\n\n"
            "Пополните баланс для активации: /balance"
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
                f"Требуется: {required} токенов\n"
                f"На балансе: {available} токенов\n\n"
                "Пополните баланс: /balance"
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
            urgency = "🔴 Критически"
        elif current_balance <= 10:
            urgency = "🟠 Очень"
        else:
            urgency = "🟡 Внимание:"

        message = (
            f"{urgency} низкий баланс токенов\n\n"
            f"На балансе: <b>{current_balance}</b> токенов\n\n"
            "Пополните баланс: /balance"
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
