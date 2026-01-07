"""Apply Analyzer service."""

from typing import AsyncIterator

import aiohttp

from .client import BaseRunnerClient, TaskResponse
from .models import StreamMessage


class ApplyAnalyzer:
    """Сервис создания отклика на вакансию через Runner."""

    ENDPOINT = "/api/vacancy/apply"

    def __init__(self, runner: BaseRunnerClient):
        self.runner = runner

    async def apply(
        self,
        vacancy_url: str,
        telegram_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """Запустить создание отклика на вакансию.

        1. POST /api/vacancy/apply -> получаем task_id и stream_url
        2. GET stream_url -> SSE стрим результатов
        """
        form = aiohttp.FormData()
        form.add_field("vacancy_url", vacancy_url)
        form.add_field("telegram_id", str(telegram_id))

        # Step 1: Create task
        result = await self.runner.create_task(self.ENDPOINT, form)

        if isinstance(result, str):
            # Error string
            yield StreamMessage(type="error", content=result)
            return

        # Notify about queue position
        if result.queue_position > 0:
            yield StreamMessage(
                type="progress",
                content=f"Задача в очереди. Позиция: {result.queue_position}",
            )

        # Step 2: Stream results
        async for message in self.runner.stream_task(result.stream_url, telegram_id):
            yield message

    async def cancel(self, telegram_id: int) -> bool:
        """Отменить создание отклика."""
        return await self.runner.cancel_stream(telegram_id)
