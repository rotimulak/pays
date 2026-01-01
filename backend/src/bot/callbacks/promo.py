"""Callback data for promo code actions."""

from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class PromoCallback(CallbackData, prefix="promo"):
    """Callback data for promo code actions.

    Examples:
        promo:apply:550e8400-e29b-41d4-a716-446655440000
        promo:remove:550e8400-e29b-41d4-a716-446655440000
        promo:skip:550e8400-e29b-41d4-a716-446655440000
    """

    action: str  # "apply", "remove", "skip", "cancel"
    tariff_id: UUID
