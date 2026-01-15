"""Constructor upload command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Document, Message

from src.bot.states.constructor import ConstructorStates
from src.core.logging import get_logger
from src.services.runner import get_runner_client

logger = get_logger(__name__)

router = Router(name="constructor")

# Limits
MAX_FILE_SIZE = 100 * 1024  # 100 KB
ALLOWED_EXTENSIONS = {".txt", ".md"}

UPLOAD_PROMPT = """
<b>Загрузка конструктора откликов</b>

Отправьте файл конструктора (.txt или .md)

Максимальный размер: <b>100 КБ</b>

Текущий конструктор можно скачать командой /get_constructor
Чтобы вернуться к автоматическому: /reset_constructor
""".strip()


@router.message(Command("constructor"))
async def cmd_constructor(message: Message, state: FSMContext) -> None:
    """Команда загрузки пользовательского конструктора."""
    await state.set_state(ConstructorStates.waiting_for_file)
    await message.answer(UPLOAD_PROMPT, parse_mode="HTML")


@router.message(ConstructorStates.waiting_for_file, F.document)
async def handle_constructor_file(message: Message, state: FSMContext) -> None:
    """Обработка загруженного файла конструктора."""
    document: Document = message.document

    # Validate extension
    filename = document.file_name or "file"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        await message.answer(
            f"Неверный формат. Поддерживаются: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        return

    # Validate size
    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await message.answer(f"Файл слишком большой. Максимум: {MAX_FILE_SIZE // 1024} КБ")
        return

    # Download file
    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)
    content = file_content.read()

    # Validate not empty
    if len(content.strip()) == 0:
        await message.answer("Файл пустой.")
        return

    await message.answer("Загружаю конструктор...")

    # Upload to Runner
    runner = get_runner_client()
    result = await runner.upload_constructor(
        telegram_id=message.from_user.id,
        content=content,
        filename=filename,
    )

    if isinstance(result, str):
        # Error
        if "CV_NOT_FOUND" in result:
            await message.answer(
                "Сначала загрузите резюме через /cv\n\n"
                "Конструктор создаётся на основе вашего резюме."
            )
        elif "SECURITY_VIOLATION" in result:
            await message.answer(
                "Файл содержит запрещённый контент и не может быть загружен."
            )
        else:
            await message.answer(f"Ошибка загрузки: {result}")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        "<b>Конструктор обновлён!</b>\n\n"
        "Теперь команда /apply будет использовать вашу версию.\n\n"
        "Чтобы вернуться к автоматическому: /reset_constructor",
        parse_mode="HTML"
    )


@router.message(ConstructorStates.waiting_for_file)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода (текст вместо файла)."""
    await message.answer(
        f"Отправьте файл .txt или .md\n\nДля отмены: /cancel"
    )


@router.message(Command("get_constructor"))
async def cmd_get_constructor(message: Message) -> None:
    """Скачать текущий конструктор."""
    runner = get_runner_client()
    result = await runner.download_constructor(telegram_id=message.from_user.id)

    if isinstance(result, str):
        if "CONSTRUCTOR_NOT_FOUND" in result:
            await message.answer(
                "Конструктор не найден.\n\n"
                "Сначала загрузите резюме через /cv"
            )
        else:
            await message.answer(f"Ошибка: {result}")
        return

    content = result.get("content", "")
    constructor_type = result.get("constructor_type", "auto")
    filename = result.get("filename", "constructor.txt")

    type_label = "пользовательский" if constructor_type == "user" else "автоматический"

    await message.answer_document(
        document=BufferedInputFile(
            content.encode("utf-8"),
            filename=filename,
        ),
        caption=f"Текущий конструктор ({type_label})"
    )


@router.message(Command("reset_constructor"))
async def cmd_reset_constructor(message: Message) -> None:
    """Удалить пользовательский конструктор."""
    runner = get_runner_client()
    result = await runner.reset_constructor(telegram_id=message.from_user.id)

    if isinstance(result, str):
        if "USER_CONSTRUCTOR_NOT_FOUND" in result:
            await message.answer(
                "У вас нет пользовательского конструктора.\n"
                "Используется автоматически сгенерированный."
            )
        else:
            await message.answer(f"Ошибка: {result}")
        return

    await message.answer(
        "<b>Пользовательский конструктор удалён</b>\n\n"
        "Теперь используется автоматически сгенерированный конструктор.",
        parse_mode="HTML"
    )
