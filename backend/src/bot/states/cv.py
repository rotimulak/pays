"""CV analysis FSM states."""

from aiogram.fsm.state import State, StatesGroup


class CVStates(StatesGroup):
    """Состояния для процесса анализа CV."""

    waiting_for_file = State()  # Ожидаем файл от пользователя
    processing = State()  # Анализ в процессе
