"""Help command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.config import settings

router = Router(name="help")

HELP_TEXT = """
❓ <b>Помощь</b>

<b>💰 Баланс</b> — проверить токены и статус подписки

<b>📋 Как это работает:</b>
1. Пополните баланс (минимум {min_payment}₽)
2. Первый платёж активирует подписку
3. Токены расходуются на запросы
4. Подписка продлевается автоматически

<b>📞 Поддержка:</b> @{support}
""".strip()


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Get help screen keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
        ]
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    """Handle /help command and menu button."""
    support = getattr(settings, "support_username", "support")
    # Default min_payment, will be updated when tariff is loaded
    min_payment = 200
    text = HELP_TEXT.format(min_payment=min_payment, support=support)
    await message.answer(text, reply_markup=get_help_keyboard())


@router.callback_query(F.data == "help")
async def on_help_callback(callback: CallbackQuery) -> None:
    """Handle help callback from inline keyboard."""
    if callback.message is None:
        await callback.answer()
        return

    support = getattr(settings, "support_username", "support")
    min_payment = 200
    text = HELP_TEXT.format(min_payment=min_payment, support=support)

    await callback.message.edit_text(text, reply_markup=get_help_keyboard())
    await callback.answer()
