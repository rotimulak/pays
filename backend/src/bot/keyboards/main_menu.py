"""Main menu keyboard."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Create main menu reply keyboard.

    Layout:
    [💰 Баланс] [❓ Помощь]
    [💪 Усилить резюме]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Баланс"),
                KeyboardButton(text="❓ Помощь"),
            ],
            [
                KeyboardButton(text="💪 Усилить резюме"),
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
            ],
        ]
    )


def get_start_menu_inline() -> InlineKeyboardMarkup:
    """Create start menu inline keyboard with main actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Анализ резюме", callback_data="cmd_cv"),
                InlineKeyboardButton(text="💪 Усилить резюме", callback_data="cmd_skills"),
            ],
            [
                InlineKeyboardButton(text="💼 Создать отклик", callback_data="cmd_apply"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            ],
        ]
    )
