"""Callback data for apply feedback."""

from aiogram.filters.callback_data import CallbackData


class FeedbackCallback(CallbackData, prefix="feedback"):
    """Callback data for feedback actions.

    Examples:
        feedback:bad:vacancy_url_hash
        feedback:ok:vacancy_url_hash
        feedback:great:vacancy_url_hash
    """

    rating: str  # "bad", "ok", "great"
    vacancy_hash: str  # Short hash of vacancy URL for identification
