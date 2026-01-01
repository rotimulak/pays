"""Callback data for tariff selection."""

from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class TariffCallback(CallbackData, prefix="tariff"):
    """Callback data for tariff actions.

    Examples:
        tariff:select:550e8400-e29b-41d4-a716-446655440000
        tariff:info:550e8400-e29b-41d4-a716-446655440000
    """

    action: str  # "select", "info"
    tariff_id: UUID
