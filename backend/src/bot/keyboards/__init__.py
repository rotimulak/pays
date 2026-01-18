"""Bot keyboards."""

from src.bot.keyboards.feedback import get_feedback_keyboard
from src.bot.keyboards.main_menu import get_back_keyboard, get_main_menu, get_start_menu_inline
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
    "get_back_keyboard",
    "get_feedback_keyboard",
    "get_main_menu",
    "get_start_menu_inline",
    "get_payment_keyboard",
    "get_payment_success_keyboard",
    "get_pending_payment_keyboard",
    "get_promo_input_keyboard",
    "get_promo_result_keyboard",
    "get_tariff_with_promo_keyboard",
]
