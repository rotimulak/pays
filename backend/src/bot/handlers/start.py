"""Start command handler."""

import os

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.healthcheck import check_runner_health
from src.bot.keyboards.main_menu import get_main_menu, get_main_menu_inline
from src.core.config import settings
from src.db.models.user import User

router = Router(name="start")

# Версия билда (устанавливается при деплое)
BUILD_VERSION = os.getenv("BUILD_VERSION", "dev")

# URL для юридических документов
OFERTA_URL = f"{settings.webhook_base_url}/legal/oferta"


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Handle /start command."""
    first_name = user.first_name or "друг"

    # Check runner health
    try:
        is_healthy, status_msg = await check_runner_health()
    except Exception:
        is_healthy = False

    if is_healthy:
        text = (
            f"Привет, {first_name}!\n\n"
            "Я помогу пользоваться сервисом и управлять своей подпиской.\n\n"
            "Выбери действие в меню ниже:\n\n"
            f'<a href="{OFERTA_URL}">Публичная оферта</a>\n\n'
            f"<i>v{BUILD_VERSION}</i>"
        )
    else:
        text = (
            f"Привет, {first_name}!\n\n"
            "⚠️ <b>К сожалению, сервис временно недоступен.</b>\n\n"
            "Мы уже работаем над восстановлением. "
            "Пожалуйста, попробуйте позже.\n\n"
            f'<a href="{OFERTA_URL}">Публичная оферта</a>\n\n'
            f"<i>v{BUILD_VERSION}</i>"
        )

    await message.answer(
        text, reply_markup=get_main_menu(), parse_mode="HTML", disable_web_page_preview=True
    )


@router.callback_query(F.data == "main_menu")
async def on_main_menu(callback: CallbackQuery) -> None:
    """Return to main menu (inline navigation)."""
    if callback.message is None:
        await callback.answer()
        return

    try:
        text = "Главное меню\n\nВыбери действие:"
        await callback.message.edit_text(text, reply_markup=get_main_menu_inline())
        await callback.answer()
    except Exception:
        await callback.answer()
