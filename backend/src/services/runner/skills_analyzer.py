"""Skills Analyzer service."""

from typing import AsyncIterator

import aiohttp

from .client import BaseRunnerClient
from .models import StreamMessage


class SkillsAnalyzer:
    """Сервис анализа навыков на основе вакансий через Runner."""

    ENDPOINT = "/api/skills/analyze"

    def __init__(self, runner: BaseRunnerClient):
        self.runner = runner

    async def analyze(
        self,
        vacancy_urls: list[str],
        telegram_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """Запустить анализ навыков по списку вакансий.

        1. POST /api/skills/analyze -> получаем task_id и stream_url
        2. GET stream_url -> SSE стрим результатов

        Args:
            vacancy_urls: Список URL вакансий на hh.ru (до 20 штук)
            telegram_id: Telegram ID пользователя
        """
        form = aiohttp.FormData()
        # Передаём список URL каждый с новой строки (API ожидает vacancies_list)
        form.add_field("vacancies_list", "\n".join(vacancy_urls))
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
        """Отменить анализ навыков."""
        return await self.runner.cancel_stream(telegram_id)
