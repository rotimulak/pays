"""Main menu keyboard."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Create main menu reply keyboard.

    M11: Simplified layout:
    [💰 Баланс] [❓ Помощь]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Баланс"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
    )


def get_main_menu_inline() -> InlineKeyboardMarkup:
    """Create main menu inline keyboard.

    Used for navigation within messages.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            ],
        ]
    )
