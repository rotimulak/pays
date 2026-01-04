"""Middleware to cancel active Runner streams on command change."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from src.services.runner import get_runner_client


class CancelRunnerMiddleware(BaseMiddleware):
    """Отменяет активный стрим Runner при смене команды."""

    TRIGGER_COMMANDS = {"/start", "/help", "/profile", "/balance", "/tariffs", "/buy", "/promo", "/history"}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            command = event.text.split()[0] if event.text else ""
            if command in self.TRIGGER_COMMANDS:
                runner = get_runner_client()
                await runner.cancel_stream(event.from_user.id)

        return await handler(event, data)
