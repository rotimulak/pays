"""Constructor upload FSM states."""

from aiogram.fsm.state import State, StatesGroup


class ConstructorStates(StatesGroup):
    """Состояния для процесса загрузки конструктора."""

    waiting_for_file = State()  # Ожидаем файл от пользователя
