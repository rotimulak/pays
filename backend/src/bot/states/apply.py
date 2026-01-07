"""Apply command FSM states."""

from aiogram.fsm.state import State, StatesGroup


class ApplyStates(StatesGroup):
    """Состояния для процесса отклика на вакансию."""

    waiting_for_url = State()  # Ожидаем URL вакансии от пользователя
    processing = State()  # Обработка в процессе
