"""Skills analysis command handler."""

import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import get_back_keyboard
from src.bot.states.skills import SkillsStates
from src.core.logging import get_logger
from src.services.skills_service import SKILLS_COST, SkillsService
from src.services.runner import SkillsAnalyzer, get_runner_client
from src.services.token_service import TokenService

logger = get_logger(__name__)

router = Router(name="skills")

# Максимум ссылок для анализа
MAX_URLS = 20

PROMPT = """
💪 <b>Усилить резюме</b>

Отправьте список ссылок на вакансии с hh.ru (до {max_urls} штук).

Я проанализирую требования и подскажу, какие ключевые слова и навыки добавить в резюме для повышения релевантности.

💰 Стоимость: <b>{cost} токен</b>

Пример:
https://hh.ru/vacancy/123456789
https://hh.ru/vacancy/987654321
""".strip()

ERROR_NO_URLS = """
❌ Ссылки не найдены!

Отправьте одну или несколько ссылок на вакансии с hh.ru.

Пример:
https://hh.ru/vacancy/123456789
https://hh.ru/vacancy/987654321
""".strip()

ERROR_TOO_MANY_URLS = """
❌ Слишком много ссылок!

Максимум можно отправить {max_urls} ссылок за раз.
Вы отправили: {count}
""".strip()

# Regex для поиска URL hh.ru в тексте
HH_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?hh\.ru/vacancy/\d+",
    re.IGNORECASE
)


def _get_skills_service(session: AsyncSession, bot) -> SkillsService:
    """Factory для SkillsService с DI."""
    runner_client = get_runner_client()
    return SkillsService(
        token_service=TokenService(session),
        skills_analyzer=SkillsAnalyzer(runner_client),
        bot=bot,
    )


def _extract_hh_urls(text: str) -> list[str]:
    """Извлечь уникальные URL hh.ru из текста."""
    urls = HH_URL_PATTERN.findall(text)
    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


@router.message(Command("skills"))
@router.message(F.text == "💪 Усилить резюме")
async def cmd_skills(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Запуск команды анализа навыков."""
    skills_service = _get_skills_service(session, message.bot)

    # Отменяем предыдущий анализ
    await skills_service.cancel(message.from_user.id)

    # Проверяем доступ до показа промпта
    can_access, _ = await skills_service.check_access(message.from_user.id)
    if not can_access:
        await message.answer(
            "У вас не активирована подписка.\n\n"
            "Воспользуйтесь пополнением баланса /balance\n\n"
            "Если у вас есть промокод введите его /promo"
        )
        return

    await state.set_state(SkillsStates.waiting_for_urls)
    await message.answer(
        PROMPT.format(cost=SKILLS_COST, max_urls=MAX_URLS),
        parse_mode="HTML",
        reply_markup=get_back_keyboard(),
    )


@router.message(SkillsStates.waiting_for_urls, F.text)
async def handle_vacancy_urls(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка списка URL вакансий."""
    text = message.text.strip()

    # Извлекаем URL из текста
    urls = _extract_hh_urls(text)

    if not urls:
        await message.answer(ERROR_NO_URLS)
        return

    if len(urls) > MAX_URLS:
        await message.answer(ERROR_TOO_MANY_URLS.format(max_urls=MAX_URLS, count=len(urls)))
        return

    # Переходим в состояние обработки
    await state.set_state(SkillsStates.processing)
    await message.answer(f"🔄 Анализирую {len(urls)} вакансий...")

    # Запускаем анализ через сервис
    skills_service = _get_skills_service(session, message.bot)
    result = await skills_service.analyze_skills(
        vacancy_urls=urls,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    # Завершаем
    if result.success:
        if result.tokens_spent > 0:
            await message.answer(f"✅ Анализ завершён! Списано: {result.tokens_spent} токен")
        else:
            await message.answer("✅ Анализ завершён!")

    await state.clear()


@router.message(SkillsStates.waiting_for_urls)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода (не текст)."""
    await message.answer(
        f"❌ Пожалуйста, отправьте ссылки на вакансии текстом.\n\n{PROMPT.format(cost=SKILLS_COST, max_urls=MAX_URLS)}"
    )
