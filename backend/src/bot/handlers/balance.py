"""Balance handler."""

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.repositories.transaction_repository import TransactionStats
from src.services.transaction_service import TransactionService

router = Router()


@router.message(Command("balance"))
async def cmd_balance(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Show current balance and subscription status."""
    service = TransactionService(session)
    stats = await service.get_user_stats(user.id)

    text = format_balance_message(user, stats)
    await message.answer(text)


def format_balance_message(user: User, stats: TransactionStats) -> str:
    """Format balance information."""
    lines = ["Ваш баланс\n"]

    # Current balance
    lines.append(f"Токены: {user.token_balance}")

    # Subscription status
    if user.subscription_end:
        now = datetime.utcnow()
        if user.subscription_end > now:
            days_left = (user.subscription_end - now).days
            lines.append(
                f"Подписка: активна до {user.subscription_end.strftime('%d.%m.%Y')}"
            )
            if days_left <= 3:
                lines.append(f"   Осталось {days_left} дней!")
        else:
            lines.append("Подписка: истекла")
    else:
        lines.append("Подписка: не активна")

    # Stats
    lines.append("\nСтатистика:")
    lines.append(f"  Всего пополнено: {stats.total_topup} токенов")
    lines.append(f"  Всего потрачено: {stats.total_spent} токенов")

    # Actions
    lines.append("\nПополнить: /tariffs")
    lines.append("История: /history")

    return "\n".join(lines)
