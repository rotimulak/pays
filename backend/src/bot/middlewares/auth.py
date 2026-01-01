"""Auth middleware for automatic user registration."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user_service import UserService

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware for automatic user registration/retrieval."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Extract user from event and get or create in database."""
        # Extract Telegram user from event
        tg_user = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            tg_user = event.from_user

        if tg_user is None:
            # No user in event (e.g., channel posts)
            return await handler(event, data)

        session: AsyncSession = data["session"]
        user_service = UserService(session)

        user, created = await user_service.get_or_create_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
        )

        if created:
            logger.info("New user registered: %d (@%s)", user.id, user.username)

        data["user"] = user
        data["user_service"] = user_service

        return await handler(event, data)
