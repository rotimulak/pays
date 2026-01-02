"""Balance keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_balance_keyboard(can_spend: bool) -> InlineKeyboardMarkup:
    """Keyboard for balance view.

    Args:
        can_spend: Whether user can spend tokens

    Returns:
        Inline keyboard with action buttons
    """
    builder = InlineKeyboardBuilder()

    if not can_spend:
        builder.button(text="Popolnit balans", callback_data="show_tariffs")

    builder.button(text="Istoriya tranzakcij", callback_data="show_history")
    builder.button(text="Obnovit", callback_data="refresh_balance")

    builder.adjust(1)
    return builder.as_markup()
