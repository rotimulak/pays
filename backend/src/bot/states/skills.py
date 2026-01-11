"""Skills analysis FSM states."""

from aiogram.fsm.state import State, StatesGroup


class SkillsStates(StatesGroup):
    """Состояния для процесса анализа навыков."""

    waiting_for_urls = State()  # Ожидаем список URL вакансий
    processing = State()  # Анализ в процессе
