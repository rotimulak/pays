"""Balance keyboards for M11 simplified UX."""

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_balance_keyboard(min_payment: Decimal = Decimal("200.00")) -> InlineKeyboardMarkup:
    """Keyboard for M11 balance screen with promo code button.

    Layout:
    [💳 Пополнить 200₽] [✏️ Другая сумма] [🎟 Промокод]
    [📋 История] [🔄 Обновить]
    [◀️ Главное меню]

    Args:
        min_payment: Minimum payment amount from tariff

    Returns:
        Inline keyboard with payment and promo buttons
    """
    min_amount = int(min_payment)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 Пополнить {min_amount}₽",
                    callback_data=f"pay:{min_amount}",
                ),
                InlineKeyboardButton(
                    text="✏️ Другая сумма",
                    callback_data="pay:custom",
                ),
                InlineKeyboardButton(
                    text="🎟 Промокод",
                    callback_data="promo_trial",
                ),
            ],
            [
                InlineKeyboardButton(text="📋 История", callback_data="show_history"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_balance"),
            ],
            [
                InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu"),
            ],
        ]
    )


def get_payment_keyboard(amount: int, payment_url: str) -> InlineKeyboardMarkup:
    """Keyboard for payment confirmation.

    Args:
        amount: Payment amount in RUB
        payment_url: URL to payment provider

    Returns:
        Inline keyboard with pay and cancel buttons
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"💳 Оплатить {amount}₽", url=payment_url),
            ],
            [
                InlineKeyboardButton(text="◀️ Отмена", callback_data="balance"),
            ],
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with just cancel button (for FSM states)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="balance")],
        ]
    )


def get_trial_promo_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for trial promo code input."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="balance")],
        ]
    )
