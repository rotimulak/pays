"""Start command handler."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.main_menu import get_main_menu, get_main_menu_inline
from src.db.models.user import User

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Handle /start command."""
    first_name = user.first_name or "друг"
    text = (
        f"👋 Привет, {first_name}!\n\n"
        "Я помогу тебе управлять балансом и подпиской.\n\n"
        "Выбери действие в меню ниже:"
    )
    await message.answer(text, reply_markup=get_main_menu())


@router.callback_query(F.data == "main_menu")
async def on_main_menu(callback: CallbackQuery) -> None:
    """Return to main menu (inline navigation)."""
    if callback.message is None:
        await callback.answer()
        return

    text = "👋 Главное меню\n\nВыбери действие:"
    await callback.message.edit_text(text, reply_markup=get_main_menu_inline())
    await callback.answer()
