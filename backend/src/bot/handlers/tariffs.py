"""Tariffs command handler.

M11: This handler now redirects to balance screen.
Tariff selection is hidden from users.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.db.models.user import User

router = Router(name="tariffs")

REDIRECT_TEXT = """
ℹ️ <b>Выбор тарифов больше не требуется</b>

Теперь просто пополняйте баланс — система автоматически
активирует и продлевает подписку.

Нажмите «Баланс» чтобы пополнить.
"""


def get_redirect_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard redirecting to balance."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        ]
    )


@router.message(Command("tariffs"))
@router.message(F.text == "💰 Тарифы")
async def cmd_tariffs(message: Message, user: User) -> None:
    """Handle /tariffs command - redirect to balance.

    M11: Tariff selection is no longer needed.
    """
    await message.answer(REDIRECT_TEXT, reply_markup=get_redirect_keyboard())


@router.callback_query(F.data == "show_tariffs")
@router.callback_query(F.data == "refresh_tariffs")
async def show_tariffs_callback(callback: CallbackQuery, user: User) -> None:
    """Handle tariff callbacks - redirect to balance."""
    if callback.message is None:
        await callback.answer()
        return

    await callback.message.edit_text(REDIRECT_TEXT, reply_markup=get_redirect_keyboard())
    await callback.answer()
