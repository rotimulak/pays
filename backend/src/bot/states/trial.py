"""FSM states for trial promo code activation."""

from aiogram.fsm.state import State, StatesGroup


class TrialStates(StatesGroup):
    """States for trial promo code activation."""

    waiting_for_code = State()
