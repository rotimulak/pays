"""Main menu keyboard."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    """Create main menu reply keyboard.

    Layout:
    [💰 Тарифы] [👤 Профиль]
    [📜 История] [❓ Помощь]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Тарифы"),
                KeyboardButton(text="👤 Профиль"),
            ],
            [
                KeyboardButton(text="📜 История"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
    )
