"""CV analysis command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Document, Message

from src.bot.states.cv import CVStates
from src.services.runner import CVFile, FileValidationError, get_cv_analyzer

router = Router(name="cv")

UPLOAD_PROMPT = """
📄 <b>Анализ CV</b>

Загрузите ваше резюме в формате <b>PDF</b> или <b>TXT</b>.

⚠️ Максимальный размер файла: <b>1 МБ</b>

Отправьте файл прямо в этот чат.
""".strip()

ERROR_MESSAGES = {
    FileValidationError.INVALID_FORMAT: "❌ Неверный формат файла. Поддерживаются только PDF и TXT.",
    FileValidationError.FILE_TOO_LARGE: "❌ Файл слишком большой. Максимум 1 МБ.",
    FileValidationError.EMPTY_FILE: "❌ Файл пустой.",
}


@router.message(Command("cv"))
async def cmd_cv(message: Message, state: FSMContext) -> None:
    """Запуск команды анализа CV."""
    # Отменяем предыдущий анализ, если был
    analyzer = get_cv_analyzer()
    await analyzer.cancel(message.from_user.id)

    await state.set_state(CVStates.waiting_for_file)
    await message.answer(UPLOAD_PROMPT)


@router.message(CVStates.waiting_for_file, F.document)
async def handle_cv_file(message: Message, state: FSMContext) -> None:
    """Обработка загруженного файла CV."""
    document: Document = message.document

    # Скачиваем файл
    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)
    content = file_content.read()

    # Валидация
    result = CVFile.validate(content, document.file_name or "file", document.mime_type or "")

    if isinstance(result, FileValidationError):
        await message.answer(ERROR_MESSAGES[result] + "\n\n" + UPLOAD_PROMPT)
        return

    cv_file: CVFile = result

    # Переходим в состояние обработки
    await state.set_state(CVStates.processing)
    await message.answer("🔄 Анализирую ваше резюме...")

    # Запускаем анализ
    analyzer = get_cv_analyzer()

    async for msg in analyzer.analyze(cv_file, message.from_user.id):
        if msg.type == "cancelled":
            break
        elif msg.type == "error":
            await message.answer(f"❌ {msg.content}")
            break
        elif msg.type == "done":
            await message.answer("✅ Анализ завершён!")
            break
        else:
            # Отправляем результат пользователю
            if msg.content:
                await message.answer(msg.content)

    await state.clear()


@router.message(CVStates.waiting_for_file)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода (текст вместо файла)."""
    await message.answer("❌ Пожалуйста, отправьте файл, а не текст.\n\n" + UPLOAD_PROMPT)
