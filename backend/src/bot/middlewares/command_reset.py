"""Middleware to reset FSM state and cancel Runner on command change."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.services.runner import get_runner_client


class CommandResetMiddleware(BaseMiddleware):
    """Сброс FSM состояния и Runner при смене команды.

    Решает проблему "зависания" бота когда пользователь
    запускает новую команду находясь в состоянии от предыдущей.
    """

    FLOW_COMMANDS = {
        "/cv",
        "/apply",
        "/skills",
        "/constructor",
        "/promo",
        "/balance",
        "/trial",
        "/start",
        "/help",
        "/profile",
        "/tariffs",
        "/buy",
        "/history",
    }

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text and event.from_user:
            command = event.text.split()[0] if event.text else ""
            if command in self.FLOW_COMMANDS:
                # 1. Очистка FSM состояния
                state: FSMContext | None = data.get("state")
                if state:
                    await state.clear()

                # 2. Отмена Runner стриминга
                try:
                    runner = get_runner_client()
                    await runner.cancel_stream(event.from_user.id)
                except Exception:
                    pass  # Не блокируем обработку команды из-за ошибки отмены

        return await handler(event, data)
