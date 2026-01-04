"""CV Analyzer service."""

from typing import AsyncIterator

import aiohttp

from .client import BaseRunnerClient
from .models import CVFile, StreamMessage


class CVAnalyzer:
    """Сервис анализа CV через Runner."""

    ENDPOINT = "/analyze-cv"

    def __init__(self, runner: BaseRunnerClient):
        self.runner = runner

    async def analyze(
        self,
        cv_file: CVFile,
        user_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """Запустить анализ CV."""
        form = aiohttp.FormData()
        form.add_field(
            "file",
            cv_file.content,
            filename=cv_file.filename,
            content_type=cv_file.mime_type,
        )
        form.add_field("user_id", str(user_id))

        async for message in self.runner.stream_request(self.ENDPOINT, form, user_id):
            yield message

    async def cancel(self, user_id: int) -> bool:
        """Отменить анализ."""
        return await self.runner.cancel_stream(user_id)
