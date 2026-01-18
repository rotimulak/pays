"""Feedback inline keyboard."""

import hashlib

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.callbacks.feedback import FeedbackCallback


def _hash_url(url: str) -> str:
    """Create short hash from URL for callback data."""
    return hashlib.md5(url.encode()).hexdigest()[:8]


def get_feedback_keyboard(vacancy_url: str) -> InlineKeyboardMarkup:
    """Create feedback keyboard with emoji buttons.

    Args:
        vacancy_url: URL of the vacancy for identification

    Returns:
        InlineKeyboardMarkup with 3 emoji buttons in a row
    """
    builder = InlineKeyboardBuilder()
    vacancy_hash = _hash_url(vacancy_url)

    # 🤮 Bad
    builder.button(
        text="🤮",
        callback_data=FeedbackCallback(rating="bad", vacancy_hash=vacancy_hash),
    )

    # 😐 OK
    builder.button(
        text="😐",
        callback_data=FeedbackCallback(rating="ok", vacancy_hash=vacancy_hash),
    )

    # 🤩 Great
    builder.button(
        text="🤩",
        callback_data=FeedbackCallback(rating="great", vacancy_hash=vacancy_hash),
    )

    builder.adjust(3)  # All 3 buttons in one row
    return builder.as_markup()
