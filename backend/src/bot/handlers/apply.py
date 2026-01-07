"""Apply to vacancy command handler."""

import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.apply import ApplyStates
from src.core.logging import get_logger
from src.services.apply_service import APPLY_COST, ApplyService
from src.services.runner import ApplyAnalyzer, get_runner_client
from src.services.token_service import TokenService

logger = get_logger(__name__)

router = Router(name="apply")

PROMPT = """
💼 <b>Отклик на вакансию</b>

Отправьте ссылку на вакансию с hh.ru.

⚠️ Требования:
• У вас должно быть загружено резюме (команда /cv)
• Ссылка должна быть с hh.ru

💰 Стоимость: <b>{cost} токен</b>

Пример: https://hh.ru/vacancy/123456789
""".strip()

ERROR_NO_CV = """
❌ Резюме не найдено!

Сначала загрузите резюме с помощью команды /cv, а затем используйте /apply для откликов на вакансии.
""".strip()

ERROR_INVALID_URL = """
❌ Неверная ссылка!

Отправьте корректную ссылку на вакансию с hh.ru.

Пример: https://hh.ru/vacancy/123456789
""".strip()

# Regex для проверки URL hh.ru
HH_URL_PATTERN = re.compile(
    r"^https?://(www\.)?hh\.ru/vacancy/\d+",
    re.IGNORECASE
)


def _get_apply_service(session: AsyncSession, bot) -> ApplyService:
    """Factory для ApplyService с DI."""
    runner_client = get_runner_client()
    return ApplyService(
        token_service=TokenService(session),
        apply_analyzer=ApplyAnalyzer(runner_client),
        bot=bot,
    )


@router.message(Command("apply"))
async def cmd_apply(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Запуск команды создания отклика на вакансию."""
    apply_service = _get_apply_service(session, message.bot)

    # Отменяем предыдущий отклик
    await apply_service.cancel(message.from_user.id)

    # Проверяем доступ до показа промпта
    can_access, reason = await apply_service.check_access(message.from_user.id)
    if not can_access:
        await message.answer(f"❌ {reason}\n\nИспользуйте /buy для пополнения.")
        return

    await state.set_state(ApplyStates.waiting_for_url)
    await message.answer(PROMPT.format(cost=APPLY_COST))


@router.message(ApplyStates.waiting_for_url, F.text)
async def handle_vacancy_url(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка URL вакансии."""
    vacancy_url = message.text.strip()

    # Валидация URL
    if not HH_URL_PATTERN.match(vacancy_url):
        await message.answer(ERROR_INVALID_URL)
        return

    # Переходим в состояние обработки
    await state.set_state(ApplyStates.processing)
    await message.answer("🔄 Создаю отклик на вакансию...")

    # Запускаем создание отклика через сервис
    apply_service = _get_apply_service(session, message.bot)
    result = await apply_service.apply_to_vacancy(
        vacancy_url=vacancy_url,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    # Завершаем
    if result.success:
        if result.tokens_spent > 0:
            await message.answer(f"✅ Отклик создан! Списано: {result.tokens_spent} токен")
        else:
            await message.answer("✅ Отклик создан!")
    elif result.error:
        # Проверяем, является ли ошибка отсутствием резюме
        error_lower = result.error.lower()
        is_cv_not_found = (
            "404" in error_lower
            or "cv not found" in error_lower
            or "резюме не найдено" in error_lower
        )
        if is_cv_not_found:
            await message.answer(ERROR_NO_CV)
        # Иначе ошибка уже отправлена через bot_output в _handle_stream_message

    await state.clear()


@router.message(ApplyStates.waiting_for_url)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода (не текст)."""
    await message.answer(
        f"❌ Пожалуйста, отправьте ссылку на вакансию текстом.\n\n{PROMPT.format(cost=APPLY_COST)}"
    )
