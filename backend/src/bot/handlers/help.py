"""Help command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.config import settings

router = Router(name="help")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    support = getattr(settings, "support_username", "support")
    text = (
        "📖 <b>Справка</b>\n\n"
        "Доступные команды:\n\n"
        "/start — начать работу\n"
        "/profile — твой профиль\n"
        "/tariffs — доступные тарифы\n"
        "/balance — текущий баланс\n"
        "/history — история транзакций\n"
        "/help — эта справка\n\n"
        f"По вопросам: @{support}"
    )
    await message.answer(text)


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message) -> None:
    """Handle help button press."""
    await cmd_help(message)
