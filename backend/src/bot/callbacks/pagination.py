"""Pagination callback data."""

from aiogram.filters.callback_data import CallbackData


class PaginationCallback(CallbackData, prefix="page"):
    """Callback data for pagination."""

    prefix: str  # "history", "invoices", etc.
    page: int
