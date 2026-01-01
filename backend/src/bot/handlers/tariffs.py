"""Tariffs command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.tariffs import get_empty_tariffs_keyboard, get_tariffs_keyboard
from src.db.models.user import User
from src.services.tariff_service import TariffService

router = Router(name="tariffs")


@router.message(Command("tariffs"))
@router.message(F.text == "💰 Тарифы")
async def cmd_tariffs(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Handle /tariffs command and menu button.

    Shows available tariffs with inline buttons for selection.
    """
    tariff_service = TariffService(session)
    tariffs = await tariff_service.get_active_tariffs()

    if not tariffs:
        await message.answer(
            "😔 К сожалению, сейчас нет доступных тарифов.\n"
            "Попробуйте позже.",
            reply_markup=get_empty_tariffs_keyboard(),
        )
        return

    # Format tariffs list
    text = tariff_service.format_tariffs_list(tariffs)

    await message.answer(
        text,
        reply_markup=get_tariffs_keyboard(tariffs),
    )


@router.callback_query(F.data == "show_tariffs")
@router.callback_query(F.data == "refresh_tariffs")
async def show_tariffs_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Handle show/refresh tariffs callback."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    tariff_service = TariffService(session)
    tariffs = await tariff_service.get_active_tariffs()

    if not tariffs:
        await message.edit_text(
            "😔 К сожалению, сейчас нет доступных тарифов.\n"
            "Попробуйте позже.",
            reply_markup=get_empty_tariffs_keyboard(),
        )
        await callback.answer()
        return

    text = tariff_service.format_tariffs_list(tariffs)

    await message.edit_text(
        text,
        reply_markup=get_tariffs_keyboard(tariffs),
    )
    await callback.answer()
