"""Runner API client."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import AsyncIterator

import aiohttp

from .models import StreamMessage


class BaseRunnerClient(ABC):
    """Абстрактный клиент для Runner API.

    Позволяет заменить реализацию без изменения бизнес-логики.
    """

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Проверка доступности Runner."""
        pass

    @abstractmethod
    async def stream_request(
        self,
        endpoint: str,
        data: aiohttp.FormData,
        user_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """Стриминговый запрос к Runner."""
        pass

    @abstractmethod
    async def cancel_stream(self, user_id: int) -> bool:
        """Отменить активный стрим для пользователя."""
        pass


class RunnerClient(BaseRunnerClient):
    """HTTP клиент для HHH Runner API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self._cancel_flags: dict[int, asyncio.Event] = {}

    async def health_check(self) -> tuple[bool, str]:
        """Проверка health endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("status", "unknown")
                        if status == "healthy":
                            return True, "healthy"
                        return False, f"status: {status}"
                    return False, f"HTTP {response.status}"
        except aiohttp.ClientError as e:
            return False, f"{type(e).__name__}"
        except TimeoutError:
            return False, "timeout"
        except Exception as e:
            return False, str(e)

    async def stream_request(
        self,
        endpoint: str,
        data: aiohttp.FormData,
        user_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """SSE стрим от Runner."""
        self._cancel_flags[user_id] = asyncio.Event()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{endpoint}",
                    data=data,
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as response:
                    if response.status != 200:
                        yield StreamMessage(type="error", content=f"HTTP {response.status}")
                        return

                    async for line in response.content:
                        if self._cancel_flags[user_id].is_set():
                            yield StreamMessage(type="cancelled", content="")
                            return

                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            try:
                                msg = json.loads(line_str[6:])
                                yield StreamMessage(
                                    type=msg.get("type", "result"),
                                    content=msg.get("content", ""),
                                    metadata=msg.get("metadata"),
                                )
                                if msg.get("type") == "done":
                                    return
                            except json.JSONDecodeError:
                                yield StreamMessage(type="result", content=line_str[6:])
        finally:
            self._cancel_flags.pop(user_id, None)

    async def cancel_stream(self, user_id: int) -> bool:
        """Отменить активный стрим для пользователя."""
        if user_id in self._cancel_flags:
            self._cancel_flags[user_id].set()
            return True
        return False
