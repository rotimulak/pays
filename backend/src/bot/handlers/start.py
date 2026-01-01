"""Start command handler."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.bot.keyboards.main_menu import get_main_menu
from src.db.models.user import User

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Handle /start command."""
    first_name = user.first_name or "друг"
    text = (
        f"Привет, {first_name}! 👋\n\n"
        "Я помогу тебе управлять подпиской и токенами.\n\n"
        "Используй меню ниже или команды:\n"
        "/profile — твой профиль\n"
        "/tariffs — доступные тарифы\n"
        "/help — справка"
    )
    await message.answer(text, reply_markup=get_main_menu())
