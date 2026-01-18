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
    [📄 Анализ резюме] [💪 Усилить резюме]
    [💼 Создать отклик] [💰 Баланс]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📄 Анализ резюме"),
                KeyboardButton(text="💪 Усилить резюме"),
            ],
            [
                KeyboardButton(text="💼 Создать отклик"),
                KeyboardButton(text="💰 Баланс"),
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


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with single Back button for navigation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
        ]
    )
