"""Apply to vacancy command handler."""

import hashlib
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks.feedback import FeedbackCallback
from src.bot.keyboards import get_back_keyboard, get_feedback_keyboard
from src.bot.states.apply import ApplyStates
from src.core.logging import get_logger
from src.db.models import ApplyFeedback, FeedbackRating
from src.services.apply_service import ApplyService
from src.services.runner import ApplyAnalyzer, get_runner_client
from src.services.token_service import TokenService

logger = get_logger(__name__)

router = Router(name="apply")

# In-memory storage for last apply data (user_id -> {vacancy_url, task_id})
# In production, consider using Redis or FSM state
_last_apply_data: dict[int, dict] = {}

PROMPT = """
💼 <b>Отклик на вакансию</b>

Отправьте ссылку на вакансию с hh.ru.

💰 Стоимость списывается автоматически после выполнения
""".strip()

ERROR_NO_CV = """
❌ Резюме не найдено!

Сначала загрузите резюме с помощью команды /cv, а затем используйте /apply для откликов на вакансии.
""".strip()

ERROR_INVALID_URL = """
❌ Неверная ссылка!

Отправьте корректную ссылку на вакансию с hh.ru.
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


async def _start_apply_flow(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Общая логика запуска создания отклика."""
    apply_service = _get_apply_service(session, message.bot)

    # Отменяем предыдущий отклик
    await apply_service.cancel(message.from_user.id)

    # Проверяем доступ до показа промпта
    can_access, _ = await apply_service.check_access(message.from_user.id)
    if not can_access:
        await message.answer(
            "У вас не активирована подписка.\n\n"
            "Воспользуйтесь пополнением баланса /balance\n\n"
            "Если у вас есть промокод введите его /promo"
        )
        return

    # Проверяем наличие CV
    has_cv = await apply_service.check_cv_exists(message.from_user.id)
    if not has_cv:
        await message.answer(ERROR_NO_CV)
        return

    await state.set_state(ApplyStates.waiting_for_url)
    await message.answer(PROMPT, parse_mode="HTML", reply_markup=get_back_keyboard())


@router.message(Command("apply"))
async def cmd_apply(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Запуск команды создания отклика на вакансию."""
    await _start_apply_flow(message, state, session)


@router.message(F.text == "💼 Создать отклик")
async def btn_apply(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка кнопки 'Создать отклик'."""
    await _start_apply_flow(message, state, session)


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
    await message.answer("🔄 Создаю отклик на вакансию")

    # Запускаем создание отклика через сервис
    apply_service = _get_apply_service(session, message.bot)
    result = await apply_service.apply_to_vacancy(
        vacancy_url=vacancy_url,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    # Завершаем
    if result.success:
        # Store apply data for feedback
        _last_apply_data[message.from_user.id] = {
            "vacancy_url": vacancy_url,
            "task_id": result.task_id,
        }

        # Show success message with feedback keyboard
        if result.tokens_spent > 0:
            success_text = f"✅ Отклик создан! Списано: {result.tokens_spent} токен\n\nКак вам генерация?"
        else:
            success_text = "✅ Отклик создан!\n\nКак вам генерация?"

        await message.answer(
            success_text,
            reply_markup=get_feedback_keyboard(vacancy_url),
        )
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
        f"❌ Пожалуйста, отправьте ссылку на вакансию текстом.\n\n{PROMPT}"
    )


def _hash_url(url: str) -> str:
    """Create short hash from URL for verification."""
    return hashlib.md5(url.encode()).hexdigest()[:8]


@router.callback_query(FeedbackCallback.filter())
async def handle_feedback(
    callback: CallbackQuery,
    callback_data: FeedbackCallback,
    session: AsyncSession,
) -> None:
    """Handle feedback button press."""
    user_id = callback.from_user.id

    # Map rating string to enum
    rating_map = {
        "bad": FeedbackRating.BAD,
        "ok": FeedbackRating.OK,
        "great": FeedbackRating.GREAT,
    }
    rating = rating_map.get(callback_data.rating)
    if not rating:
        await callback.answer("Ошибка: неверный рейтинг")
        return

    # Get stored apply data
    apply_data = _last_apply_data.get(user_id, {})
    vacancy_url = apply_data.get("vacancy_url")
    task_id = apply_data.get("task_id")

    # Verify vacancy hash matches (optional security check)
    if vacancy_url and _hash_url(vacancy_url) != callback_data.vacancy_hash:
        vacancy_url = None  # Hash mismatch, use None

    # Save feedback to database
    feedback = ApplyFeedback(
        user_id=user_id,
        rating=rating,
        vacancy_url=vacancy_url,
        task_id=task_id,
    )
    session.add(feedback)
    await session.commit()

    # Clean up stored data
    _last_apply_data.pop(user_id, None)

    # Show emoji response based on rating
    emoji_response = {
        FeedbackRating.BAD: "Спасибо за честность! Будем улучшаться 🙏",
        FeedbackRating.OK: "Спасибо за отзыв! 👍",
        FeedbackRating.GREAT: "Рады, что понравилось! 🎉",
    }

    await callback.answer(emoji_response[rating])

    # Update message to show selected feedback
    emoji_display = {"bad": "🤮", "ok": "😐", "great": "🤩"}
    await callback.message.edit_text(
        f"{callback.message.text}\n\nВаша оценка: {emoji_display[callback_data.rating]}",
        reply_markup=None,
    )
