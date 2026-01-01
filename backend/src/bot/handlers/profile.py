"""Profile command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.models.user import User
from src.services.user_service import UserService

router = Router(name="profile")


@router.message(Command("profile", "me"))
async def cmd_profile(message: Message, user: User, user_service: UserService) -> None:
    """Handle /profile and /me commands."""
    profile = await user_service.get_user_profile(user.id)
    if profile is None:
        await message.answer("Ошибка: профиль не найден.")
        return

    username_display = f"@{profile.username}" if profile.username else "не указан"
    text = (
        "📊 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{profile.id}</code>\n"
        f"👤 Username: {username_display}\n\n"
        f"💰 Баланс: <b>{profile.token_balance}</b> токенов\n"
        f"📅 Подписка: {profile.subscription_status_text}\n\n"
        "Пополнить баланс: /tariffs"
    )
    await message.answer(text)


@router.message(F.text == "👤 Профиль")
async def btn_profile(message: Message, user: User, user_service: UserService) -> None:
    """Handle profile button press."""
    await cmd_profile(message, user, user_service)
