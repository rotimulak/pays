"""CV Analyzer service."""

from typing import AsyncIterator

import aiohttp

from .client import BaseRunnerClient, TaskResponse
from .models import CVFile, StreamMessage


class CVAnalyzer:
    """Сервис анализа CV через Runner."""

    ENDPOINT = "/analyze-cv"

    def __init__(self, runner: BaseRunnerClient):
        self.runner = runner

    async def analyze(
        self,
        cv_file: CVFile,
        telegram_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """Запустить анализ CV.

        1. POST /analyze-cv -> получаем task_id и stream_url
        2. GET stream_url -> SSE стрим результатов
        """
        form = aiohttp.FormData()
        form.add_field(
            "file",
            cv_file.content,
            filename=cv_file.filename,
            content_type=cv_file.mime_type,
        )
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
        """Отменить анализ."""
        return await self.runner.cancel_stream(telegram_id)
