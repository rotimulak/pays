"""Bot keyboards."""

from src.bot.keyboards.main_menu import get_main_menu
from src.bot.keyboards.payment import (
    get_payment_keyboard,
    get_payment_success_keyboard,
    get_pending_payment_keyboard,
)
from src.bot.keyboards.promo import (
    get_promo_input_keyboard,
    get_promo_result_keyboard,
    get_tariff_with_promo_keyboard,
)

__all__ = [
    "get_main_menu",
    "get_payment_keyboard",
    "get_payment_success_keyboard",
    "get_pending_payment_keyboard",
    "get_promo_input_keyboard",
    "get_promo_result_keyboard",
    "get_tariff_with_promo_keyboard",
]
