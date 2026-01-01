"""FSM states for promo code input."""

from aiogram.fsm.state import State, StatesGroup


class PromoStates(StatesGroup):
    """FSM states for promo code input."""

    waiting_for_code = State()
    """User should enter promo code."""

    confirming_purchase = State()
    """User confirms purchase with applied promo."""
