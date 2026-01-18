"""Runner API client."""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

import aiohttp

from src.core.logging import get_logger
from .models import StreamMessage, TaskResult

logger = get_logger(__name__)


@dataclass
class TaskResponse:
    """Response from task creation."""

    task_id: str
    status: str
    queue_position: int
    stream_url: str


class BaseRunnerClient(ABC):
    """Абстрактный клиент для Runner API.

    Позволяет заменить реализацию без изменения бизнес-логики.
    """

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Проверка доступности Runner."""
        pass

    @abstractmethod
    async def create_task(
        self,
        endpoint: str,
        data: aiohttp.FormData,
    ) -> TaskResponse | str:
        """Создать задачу. Возвращает TaskResponse или строку ошибки."""
        pass

    @abstractmethod
    async def stream_task(
        self,
        stream_url: str,
        user_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """SSE стрим задачи."""
        pass

    @abstractmethod
    async def cancel_stream(self, user_id: int) -> bool:
        """Отменить активный стрим для пользователя."""
        pass

    @abstractmethod
    async def get_result(self, task_id: str) -> TaskResult | str:
        """Получить результат задачи (JSON с content). Возвращает TaskResult или строку ошибки."""
        pass

    @abstractmethod
    async def download_result(self, task_id: str) -> bytes | str:
        """Скачать файл результата. Возвращает bytes или строку ошибки."""
        pass

    @abstractmethod
    async def check_cv_exists(self, user_id: int) -> bool:
        """Проверить наличие CV пользователя.

        Returns:
            True если CV загружено, False иначе
        """
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

    async def create_task(
        self,
        endpoint: str,
        data: aiohttp.FormData,
    ) -> TaskResponse | str:
        """Создать задачу на Runner."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{endpoint}",
                    data=data,
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        # Попытаемся получить detail из JSON для более понятной ошибки
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("detail", f"HTTP {response.status}")
                        except Exception:
                            error_msg = f"HTTP {response.status}"
                        logger.error(f"Runner API error: {error_msg}")
                        return error_msg

                    resp_data = await response.json()
                    return TaskResponse(
                        task_id=resp_data["task_id"],
                        status=resp_data["status"],
                        queue_position=resp_data.get("queue_position", 0),
                        stream_url=resp_data["stream_url"],
                    )
        except aiohttp.ClientError as e:
            return f"{type(e).__name__}: {e}"
        except KeyError as e:
            return f"Invalid response: missing {e}"
        except Exception as e:
            return str(e)

    async def stream_task(
        self,
        stream_url: str,
        user_id: int,
    ) -> AsyncIterator[StreamMessage]:
        """SSE стрим задачи."""
        self._cancel_flags[user_id] = asyncio.Event()
        full_url = f"{self.base_url}{stream_url}"

        # Извлекаем task_id из URL: /api/tasks/{task_id}/stream
        task_id = stream_url.split("/")[3] if "/tasks/" in stream_url else None

        logger.info(f"Starting stream from {full_url}")

        try:
            # Увеличиваем таймаут для долгих операций и читаем чанками для больших SSE
            timeout = aiohttp.ClientTimeout(total=600, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    full_url,
                    headers={"X-API-Key": self.api_key},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Stream error: HTTP {response.status}, body: {error_text[:200]}")
                        yield StreamMessage(type="error", content=f"HTTP {response.status}: {error_text[:100]}")
                        return

                    has_data = False
                    buffer = b""

                    # Читаем чанками, чтобы избежать "Chunk too big"
                    async for chunk in response.content.iter_chunked(1024 * 1024):  # 1 МБ чанки
                        if self._cancel_flags[user_id].is_set():
                            yield StreamMessage(type="cancelled", content="")
                            return

                        buffer += chunk

                        # Разбиваем buffer на строки
                        while b"\n" in buffer:
                            line_bytes, buffer = buffer.split(b"\n", 1)

                            try:
                                line_str = line_bytes.decode("utf-8").strip()
                            except UnicodeDecodeError:
                                logger.warning("Failed to decode SSE line, skipping")
                                continue

                            if not line_str:
                                continue

                            logger.info(f"SSE line: {line_str[:200]}")

                            if line_str.startswith("data: "):
                                has_data = True
                                try:
                                    msg = json.loads(line_str[6:])
                                    msg_type = msg.get("type", "result")
                                    msg_content = msg.get("content", "")

                                    if msg_type == "error" and not msg_content:
                                        msg_content = "Неизвестная ошибка сервера"

                                    # Обработка bot_output с дополнительными полями
                                    if msg_type == "bot_output":
                                        yield StreamMessage(
                                            type="bot_output",
                                            content=msg_content,
                                            output_type=msg.get("output_type"),
                                            filename=msg.get("filename"),
                                            caption=msg.get("caption"),
                                            format=msg.get("format"),  # "markdown" | None
                                            metadata=msg,  # Сохраняем весь JSON для доступа к track_cost полям
                                        )
                                        continue

                                    # Обработка track_cost события
                                    if msg_type == "track_cost":
                                        yield StreamMessage(
                                            type="track_cost",
                                            content="",
                                            track_cost_data=msg,
                                        )
                                        continue

                                    # Передаём task_id в complete/done сообщениях
                                    yield StreamMessage(
                                        type=msg_type,
                                        content=msg_content,
                                        metadata=msg.get("metadata"),
                                        task_id=task_id if msg_type in ("done", "complete") else None,
                                    )
                                    if msg_type in ("done", "complete"):
                                        return
                                except json.JSONDecodeError:
                                    yield StreamMessage(type="result", content=line_str[6:])

                    if not has_data:
                        logger.warning("Stream ended without data")
                        yield StreamMessage(type="error", content="Стрим завершился без данных")

        except aiohttp.ClientError as e:
            logger.error(f"Stream client error: {e}")
            yield StreamMessage(type="error", content=f"Ошибка соединения: {type(e).__name__}")
        except Exception as e:
            logger.exception(f"Stream unexpected error: {e}")
            yield StreamMessage(type="error", content=f"Ошибка: {e}")
        finally:
            self._cancel_flags.pop(user_id, None)

    async def cancel_stream(self, user_id: int) -> bool:
        """Отменить активный стрим для пользователя."""
        if user_id in self._cancel_flags:
            self._cancel_flags[user_id].set()
            return True
        return False

    async def get_result(self, task_id: str) -> TaskResult | str:
        """Получить результат задачи (JSON с content)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tasks/{task_id}/result",
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Get result error: HTTP {response.status}, body: {error_text[:200]}")
                        return f"HTTP {response.status}"

                    data = await response.json()
                    return TaskResult(
                        task_id=data.get("task_id", task_id),
                        status=data.get("status", "unknown"),
                        result_file=data.get("result_file"),
                        content=data.get("content", ""),
                    )
        except aiohttp.ClientError as e:
            logger.error(f"Get result client error: {e}")
            return f"{type(e).__name__}: {e}"
        except Exception as e:
            logger.exception(f"Get result unexpected error: {e}")
            return str(e)

    async def download_result(self, task_id: str) -> bytes | str:
        """Скачать файл результата."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tasks/{task_id}/result/download",
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Download result error: HTTP {response.status}, body: {error_text[:200]}")
                        return f"HTTP {response.status}"

                    return await response.read()
        except aiohttp.ClientError as e:
            logger.error(f"Download result client error: {e}")
            return f"{type(e).__name__}: {e}"
        except Exception as e:
            logger.exception(f"Download result unexpected error: {e}")
            return str(e)

    async def upload_constructor(
        self,
        telegram_id: int,
        content: bytes,
        filename: str = "constructor.txt",
    ) -> dict | str:
        """Загрузить пользовательский конструктор."""
        try:
            form = aiohttp.FormData()
            form.add_field("telegram_id", str(telegram_id))
            form.add_field(
                "file",
                content,
                filename=filename,
                content_type="text/plain; charset=utf-8",
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/constructor-user",
                    data=form,
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    data = await response.json()

                    if response.status == 200:
                        return data

                    detail = data.get("detail", {})
                    if isinstance(detail, dict):
                        error_code = detail.get("error_code", "UNKNOWN")
                        error_msg = detail.get("message", f"HTTP {response.status}")
                        return f"{error_code}: {error_msg}"
                    return f"HTTP {response.status}: {detail}"

        except aiohttp.ClientError as e:
            logger.error(f"Upload constructor client error: {e}")
            return f"{type(e).__name__}: {e}"
        except Exception as e:
            logger.exception(f"Upload constructor unexpected error: {e}")
            return str(e)

    async def download_constructor(self, telegram_id: int) -> dict | str:
        """Скачать текущий конструктор (user или auto)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/constructor-user",
                    params={"telegram_id": str(telegram_id)},
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    data = await response.json()

                    if response.status == 200:
                        return data

                    detail = data.get("detail", {})
                    if isinstance(detail, dict):
                        error_code = detail.get("error_code", "UNKNOWN")
                        error_msg = detail.get("message", f"HTTP {response.status}")
                        return f"{error_code}: {error_msg}"
                    return f"HTTP {response.status}: {detail}"

        except aiohttp.ClientError as e:
            logger.error(f"Download constructor client error: {e}")
            return f"{type(e).__name__}: {e}"
        except Exception as e:
            logger.exception(f"Download constructor unexpected error: {e}")
            return str(e)

    async def reset_constructor(self, telegram_id: int) -> dict | str:
        """Удалить пользовательский конструктор."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/api/constructor-user",
                    params={"telegram_id": str(telegram_id)},
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    data = await response.json()

                    if response.status == 200:
                        return data

                    detail = data.get("detail", {})
                    if isinstance(detail, dict):
                        error_code = detail.get("error_code", "UNKNOWN")
                        error_msg = detail.get("message", f"HTTP {response.status}")
                        return f"{error_code}: {error_msg}"
                    return f"HTTP {response.status}: {detail}"

        except aiohttp.ClientError as e:
            logger.error(f"Reset constructor client error: {e}")
            return f"{type(e).__name__}: {e}"
        except Exception as e:
            logger.exception(f"Reset constructor unexpected error: {e}")
            return str(e)

    async def check_cv_exists(self, user_id: int) -> bool:
        """Проверить наличие CV через GET /api/cv/{user_id}.

        Graceful degradation: если endpoint не готов или ошибка,
        возвращаем True чтобы не блокировать пользователей.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/cv/{user_id}",
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        return True
                    elif response.status == 404:
                        return False
                    else:
                        # Graceful degradation: если endpoint не готов
                        logger.warning(
                            f"CV check returned unexpected status {response.status}, "
                            f"allowing apply to proceed"
                        )
                        return True
        except aiohttp.ClientError as e:
            logger.warning(f"CV check connection error: {e}, allowing apply to proceed")
            return True
        except Exception as e:
            logger.warning(f"CV check error: {e}, allowing apply to proceed")
            return True
