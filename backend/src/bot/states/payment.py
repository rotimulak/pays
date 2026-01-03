"""Payment FSM states for M11."""

from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """States for custom amount payment flow."""

    waiting_for_amount = State()
