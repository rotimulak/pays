"""Payment inline keyboards."""

from uuid import UUID

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.callbacks.invoice import InvoiceCallback


def get_payment_keyboard(
    payment_url: str,
    amount: str,
    invoice_id: UUID,
) -> InlineKeyboardMarkup:
    """Create payment keyboard with URL button and cancel option.

    Args:
        payment_url: URL for payment gateway
        amount: Formatted amount string (e.g., "499 ₽")
        invoice_id: Invoice UUID for cancel callback

    Returns:
        InlineKeyboardMarkup with payment and cancel buttons
    """
    builder = InlineKeyboardBuilder()

    # URL button (opens payment page)
    builder.button(
        text=f"💳 Оплатить {amount}",
        url=payment_url,
    )

    # Cancel button
    builder.button(
        text="❌ Отменить",
        callback_data=InvoiceCallback(
            action="cancel",
            invoice_id=invoice_id,
        ),
    )

    builder.adjust(1)
    return builder.as_markup()


def get_pending_payment_keyboard(
    payment_url: str,
    amount: str,
    invoice_id: UUID,
) -> InlineKeyboardMarkup:
    """Create keyboard for pending invoice with check status button.

    Args:
        payment_url: URL for payment gateway
        amount: Formatted amount string
        invoice_id: Invoice UUID

    Returns:
        InlineKeyboardMarkup with payment, check, and cancel buttons
    """
    builder = InlineKeyboardBuilder()

    # URL button
    builder.button(
        text=f"💳 Оплатить {amount}",
        url=payment_url,
    )

    # Check status button
    builder.button(
        text="🔄 Проверить статус",
        callback_data=InvoiceCallback(
            action="check",
            invoice_id=invoice_id,
        ),
    )

    # Cancel button
    builder.button(
        text="❌ Отменить",
        callback_data=InvoiceCallback(
            action="cancel",
            invoice_id=invoice_id,
        ),
    )

    builder.adjust(1)
    return builder.as_markup()


def get_payment_success_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown after successful payment."""
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Мой профиль", callback_data="show_profile")
    builder.button(text="💰 Баланс", callback_data="balance")
    builder.adjust(2)
    return builder.as_markup()
