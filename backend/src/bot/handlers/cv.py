"""CV analysis command handler."""

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Document, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.cv import CVStates
from src.core.logging import get_logger
from src.services.cv_service import CV_ANALYSIS_COST, CVService
from src.services.runner import CVFile, FileValidationError, get_cv_analyzer
from src.services.token_service import TokenService

logger = get_logger(__name__)

router = Router(name="cv")

ASSETS_DIR = Path(__file__).parent.parent / "assets"

UPLOAD_PROMPT = """
📄 <b>Анализ CV</b>

Загрузите ваше резюме в формате <b>PDF</b> или <b>TXT</b>.

⚠️ Максимальный размер файла: <b>1 МБ</b>
💰 Стоимость: <b>{cost} токен</b>

Отправьте файл прямо в этот чат.
""".strip()

ERROR_MESSAGES = {
    FileValidationError.INVALID_FORMAT: "❌ Неверный формат файла. Поддерживаются только PDF и TXT.",
    FileValidationError.FILE_TOO_LARGE: "❌ Файл слишком большой. Максимум 1 МБ.",
    FileValidationError.EMPTY_FILE: "❌ Файл пустой.",
}


def _get_cv_service(session: AsyncSession, bot) -> CVService:
    """Factory для CVService с DI."""
    return CVService(
        token_service=TokenService(session),
        cv_analyzer=get_cv_analyzer(),
        bot=bot,
    )


async def _start_cv_flow(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Общая логика запуска анализа CV."""
    cv_service = _get_cv_service(session, message.bot)

    # Отменяем предыдущий анализ
    await cv_service.cancel(message.from_user.id)

    # Проверяем доступ до показа промпта
    can_access, _ = await cv_service.check_access(message.from_user.id)
    if not can_access:
        await message.answer(
            "У вас не активирована подписка.\n\n"
            "Воспользуйтесь пополнением баланса /balance\n\n"
            "Если у вас есть промокод введите его /promo"
        )
        return

    await state.set_state(CVStates.waiting_for_file)
    await message.answer(UPLOAD_PROMPT.format(cost=CV_ANALYSIS_COST), parse_mode="HTML")

    # Отправляем инструкцию по скачиванию резюме
    try:
        photo = FSInputFile(ASSETS_DIR / "how-download-android.jpg")
        await message.answer_photo(
            photo,
            caption="📱 Как скачать резюме с hh.ru на Android"
        )
    except Exception as e:
        logger.error(f"Failed to send instruction image: {e}", exc_info=True)


@router.message(Command("cv"))
async def cmd_cv(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Запуск команды анализа CV."""
    await _start_cv_flow(message, state, session)


@router.message(F.text == "📄 Анализ резюме")
async def btn_cv(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка кнопки 'Анализ резюме'."""
    await _start_cv_flow(message, state, session)


@router.message(CVStates.waiting_for_file, F.document)
async def handle_cv_file(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка загруженного файла CV."""
    document: Document = message.document

    # Скачиваем и валидируем файл
    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)
    content = file_content.read()

    result = CVFile.validate(content, document.file_name or "file", document.mime_type or "")

    if isinstance(result, FileValidationError):
        await message.answer(ERROR_MESSAGES[result])
        return

    cv_file: CVFile = result

    # Переходим в состояние обработки
    await state.set_state(CVStates.processing)
    await message.answer("🔄 Анализирую ваше резюме")

    # Запускаем анализ через сервис
    cv_service = _get_cv_service(session, message.bot)
    analysis_result = await cv_service.analyze_cv(
        cv_file=cv_file,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    # Завершаем
    if analysis_result.success:
        if analysis_result.tokens_spent > 0:
            await message.answer(f"✅ Анализ завершён! Списано: {analysis_result.tokens_spent} токен")
        else:
            await message.answer("✅ Анализ завершён!")

    await state.clear()


@router.message(CVStates.waiting_for_file)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода (текст вместо файла)."""
    await message.answer(
        f"❌ Пожалуйста, отправьте файл, а не текст.\n\n{UPLOAD_PROMPT.format(cost=CV_ANALYSIS_COST)}"
    )
