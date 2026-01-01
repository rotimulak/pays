"""Transaction history handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks.pagination import PaginationCallback
from src.db.models.user import User
from src.services.dto.transaction import TransactionDTO
from src.services.transaction_service import TransactionService

router = Router()

ITEMS_PER_PAGE = 10


@router.message(Command("history"))
async def cmd_history(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Show transaction history."""
    service = TransactionService(session)
    result = await service.get_user_transactions(
        user_id=user.id,
        limit=ITEMS_PER_PAGE,
        offset=0,
    )

    text = format_history_message(result.items, result.total, 1)
    keyboard = get_pagination_keyboard(
        current_page=1,
        total_items=result.total,
        items_per_page=ITEMS_PER_PAGE,
        callback_prefix="history",
    )

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(PaginationCallback.filter(F.prefix == "history"))
async def history_pagination(
    callback: CallbackQuery,
    callback_data: PaginationCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Handle history pagination."""
    service = TransactionService(session)

    offset = (callback_data.page - 1) * ITEMS_PER_PAGE
    result = await service.get_user_transactions(
        user_id=user.id,
        limit=ITEMS_PER_PAGE,
        offset=offset,
    )

    text = format_history_message(result.items, result.total, callback_data.page)
    keyboard = get_pagination_keyboard(
        current_page=callback_data.page,
        total_items=result.total,
        items_per_page=ITEMS_PER_PAGE,
        callback_prefix="history",
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def format_history_message(
    transactions: list[TransactionDTO],
    total: int,
    page: int,
) -> str:
    """Format transaction history for display."""
    if not transactions:
        return (
            "История транзакций\n\n"
            "У вас пока нет транзакций.\n\n"
            "Пополните баланс: /tariffs"
        )

    lines = ["История транзакций\n"]

    for tx in transactions:
        lines.append(
            f"{tx.type_display}\n"
            f"  {tx.tokens_delta_display} токенов -> {tx.balance_after}\n"
            f"  {tx.created_at_display}\n"
        )

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    lines.append(f"\nСтраница {page} из {total_pages}")

    return "\n".join(lines)


def get_pagination_keyboard(
    current_page: int,
    total_items: int,
    items_per_page: int,
    callback_prefix: str,
):
    """Create pagination keyboard."""
    total_pages = (total_items + items_per_page - 1) // items_per_page

    if total_pages <= 1:
        return None

    builder = InlineKeyboardBuilder()

    if current_page > 1:
        builder.button(
            text="< Назад",
            callback_data=PaginationCallback(
                prefix=callback_prefix,
                page=current_page - 1,
            ),
        )

    if current_page < total_pages:
        builder.button(
            text="Вперед >",
            callback_data=PaginationCallback(
                prefix=callback_prefix,
                page=current_page + 1,
            ),
        )

    builder.adjust(2)
    return builder.as_markup()
