"""Balance handler."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.balance import get_balance_keyboard
from src.db.models.user import User
from src.db.repositories.transaction_repository import TransactionStats
from src.services.token_service import TokenService
from src.services.transaction_service import TransactionService

router = Router()


@router.message(Command("balance"))
async def cmd_balance(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Show detailed balance information."""
    token_service = TokenService(session)
    transaction_service = TransactionService(session)

    # Get balance info
    balance = await token_service.check_balance(user.id)

    # Get stats
    stats = await transaction_service.get_user_stats(user.id)
    recent_spend = await transaction_service.get_recent_spending(user.id, days=7)

    text = format_detailed_balance(balance, stats, recent_spend)
    keyboard = get_balance_keyboard(balance.can_spend)

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "refresh_balance")
async def on_refresh_balance(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Refresh balance information."""
    token_service = TokenService(session)
    transaction_service = TransactionService(session)

    balance = await token_service.check_balance(user.id)
    stats = await transaction_service.get_user_stats(user.id)
    recent_spend = await transaction_service.get_recent_spending(user.id, days=7)

    text = format_detailed_balance(balance, stats, recent_spend)
    keyboard = get_balance_keyboard(balance.can_spend)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("Obnovleno")


def format_detailed_balance(
    balance,
    stats: TransactionStats,
    recent_spend: int,
) -> str:
    """Format detailed balance message."""
    lines = ["<b>Vash balans</b>\n"]

    # Current balance with status indicator
    if balance.token_balance > 50:
        balance_icon = "zelenyj"
    elif balance.token_balance > 10:
        balance_icon = "zheltyj"
    else:
        balance_icon = "krasnyj"

    lines.append(f"{balance_icon} Tokeny: <b>{balance.token_balance}</b>")

    # Subscription status
    if balance.subscription_active:
        days_left = (balance.subscription_end - datetime.utcnow()).days
        if days_left <= 3:
            sub_icon = "vnimanie"
        else:
            sub_icon = "ok"
        lines.append(
            f"{sub_icon} Podpiska: do {balance.subscription_end.strftime('%d.%m.%Y')}"
        )
        if days_left <= 3:
            lines.append(f"   <i>Ostalos {days_left} dnej</i>")
    else:
        lines.append("x Podpiska: <b>ne aktivna</b>")

    # Spending status
    lines.append("")
    if balance.can_spend:
        lines.append("ok Spisanie tokenov: <b>dostupno</b>")
    else:
        lines.append(f"x Spisanie tokenov: {balance.reason}")

    # Stats
    if stats:
        lines.append("\n<b>Statistika</b>")
        lines.append(f"   Vsego polucheno: {stats.total_topup} tokenov")
        lines.append(f"   Vsego potracheno: {stats.total_spent} tokenov")

    # Recent spending
    if recent_spend:
        lines.append(f"\nZa poslednie 7 dnej:")
        lines.append(f"   Potracheno: {recent_spend} tokenov")
        avg_daily = recent_spend / 7
        lines.append(f"   V srednem: {avg_daily:.1f} tokenov/den")

    # Actions
    lines.append("\n")
    if not balance.can_spend:
        lines.append("Popolnit: /tariffs")
    lines.append("Istoriya: /history")

    return "\n".join(lines)
