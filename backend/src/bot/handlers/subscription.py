"""Subscription management handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import get_bot
from src.core.config import settings
from src.db.models.user import User
from src.services.notification_service import NotificationService
from src.services.subscription_service import SubscriptionService

router = Router(name="subscription")


def get_subscription_keyboard(sub_status: dict) -> InlineKeyboardMarkup:
    """Build subscription management keyboard."""
    buttons = []

    # Renew button if subscription is expiring or expired
    if sub_status["status"] in ("expired", "active") and sub_status.get("days_left", 0) <= 7:
        if sub_status["can_auto_renew"]:
            buttons.append([
                InlineKeyboardButton(
                    text=f"Prodlit za {sub_status['renewal_price']} tokenov",
                    callback_data="subscription:renew",
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="Popolnit balans",
                    callback_data="tariffs",
                )
            ])

    # Auto-renew toggle
    if sub_status["auto_renew"]:
        auto_text = "Otklyuchit avtoprodlenie"
    else:
        auto_text = "Vklyuchit avtoprodlenie"

    buttons.append([
        InlineKeyboardButton(
            text=auto_text,
            callback_data="subscription:toggle_auto",
        )
    ])

    # Refresh button
    buttons.append([
        InlineKeyboardButton(
            text="Obnovit",
            callback_data="subscription:refresh",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_subscription_message(user: User, sub_status: dict) -> str:
    """Format subscription status message."""
    lines = ["<b>Upravlenie podpiskoj</b>\n"]

    # Status
    status_icons = {
        "active": "ok",
        "expired": "x",
        "none": "!",
    }
    icon = status_icons.get(sub_status["status"], "?")
    lines.append(f"{icon} Status: <b>{sub_status['status_text']}</b>")

    # End date
    if sub_status["end_date"]:
        lines.append(
            f"   Data okonchaniya: {sub_status['end_date'].strftime('%d.%m.%Y %H:%M')}"
        )

    # Days left
    if sub_status["days_left"] is not None and sub_status["days_left"] > 0:
        lines.append(f"   Ostalos: {sub_status['days_left']} dnej")

    # Auto-renew status
    lines.append("")
    if sub_status["auto_renew"]:
        lines.append("ok Avtoprodlenie: <b>vklyucheno</b>")
        if sub_status["can_auto_renew"]:
            lines.append(
                f"   Pri istechenii spishetsya {sub_status['renewal_price']} tokenov"
            )
        else:
            lines.append(
                f"   <i>Nedostatochno tokenov (nuzhno {sub_status['renewal_price']})</i>"
            )
    else:
        lines.append("x Avtoprodlenie: <b>otklyucheno</b>")

    # Balance info
    lines.append("")
    balance_rounded = round(float(user.token_balance), 2)
    generations = int(balance_rounded / 2)
    lines.append(f"Vash balans: <b>{balance_rounded}</b> tokenov (~{generations} generacij)")
    lines.append(f"Stoimost prodleniya: {sub_status['renewal_price']} tokenov")

    # Help
    lines.append("\nPopolnit balans: /tariffs")

    return "\n".join(lines)


@router.message(Command("subscription", "sub"))
async def cmd_subscription(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Show subscription details and management options."""
    notification_service = NotificationService(get_bot())
    subscription_service = SubscriptionService(session, notification_service)

    sub_status = await subscription_service.get_subscription_status(user)

    text = format_subscription_message(user, sub_status)
    keyboard = get_subscription_keyboard(sub_status)

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "subscription:refresh")
async def on_refresh_subscription(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Refresh subscription status."""
    if callback.message is None:
        await callback.answer()
        return

    try:
        notification_service = NotificationService(get_bot())
        subscription_service = SubscriptionService(session, notification_service)

        # Refresh user from DB
        from src.db.repositories.user_repository import UserRepository
        user_repo = UserRepository(session)
        fresh_user = await user_repo.get_by_id(user.id)

        if fresh_user is None:
            await callback.answer("Ошибка: пользователь не найден")
            return

        sub_status = await subscription_service.get_subscription_status(fresh_user)

        text = format_subscription_message(fresh_user, sub_status)
        keyboard = get_subscription_keyboard(sub_status)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("Обновлено")
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "subscription:toggle_auto")
async def on_toggle_auto_renew(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Toggle auto-renewal setting."""
    if callback.message is None:
        await callback.answer()
        return

    try:
        notification_service = NotificationService(get_bot())
        subscription_service = SubscriptionService(session, notification_service)

        new_value = await subscription_service.toggle_auto_renew(user.id)

        if new_value:
            await callback.answer("Автопродление включено")
        else:
            await callback.answer("Автопродление отключено")

        # Refresh the message
        from src.db.repositories.user_repository import UserRepository
        user_repo = UserRepository(session)
        fresh_user = await user_repo.get_by_id(user.id)

        if fresh_user:
            sub_status = await subscription_service.get_subscription_status(fresh_user)
            text = format_subscription_message(fresh_user, sub_status)
            keyboard = get_subscription_keyboard(sub_status)
            await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception:
        await callback.answer()


@router.callback_query(F.data == "subscription:renew")
async def on_renew_subscription(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Manually renew subscription."""
    if callback.message is None:
        await callback.answer()
        return

    try:
        notification_service = NotificationService(get_bot())
        subscription_service = SubscriptionService(session, notification_service)

        renewal_price = settings.subscription_renewal_price

        # Check balance first
        if user.token_balance < renewal_price:
            balance_rounded = round(float(user.token_balance), 2)
            await callback.answer(
                f"Недостаточно токенов. Нужно: {renewal_price}, есть: {balance_rounded}",
                show_alert=True,
            )
            return

        success = await subscription_service.manual_renew(user.id)

        if success:
            await callback.answer(
                f"Подписка продлена на {settings.subscription_renewal_days} дней!",
                show_alert=True,
            )

            # Refresh the message
            from src.db.repositories.user_repository import UserRepository
            user_repo = UserRepository(session)
            fresh_user = await user_repo.get_by_id(user.id)

            if fresh_user:
                sub_status = await subscription_service.get_subscription_status(fresh_user)
                text = format_subscription_message(fresh_user, sub_status)
                keyboard = get_subscription_keyboard(sub_status)
                await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.answer(
                "Не удалось продлить подписку. Проверьте баланс.",
                show_alert=True,
            )

    except Exception:
        await callback.answer()
