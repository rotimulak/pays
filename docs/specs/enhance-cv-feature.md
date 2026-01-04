# Спецификация: Анализ CV

> Версия: 1.1
> Статус: Draft
> Дата: 2026-01-05

---

## 1. Обзор

Добавление команды `/cv` в бот для анализа резюме пользователя через внешний HHH Runner сервис.

### Ключевые требования

- Абстрактный слой для работы с Runner (легко заменяемый)
- Загрузка CV в формате PDF или TXT (до 1 МБ)
- Отправка файла на Runner
- Получение стриминговых ответов от Runner
- Отмена при переключении на другую команду

---

## 2. Архитектура

### 2.1 Слои абстракции

```
┌─────────────────────────────────────────────────────────────┐
│                     Bot Handlers                            │
│  (cv.py - команды, состояния, UI)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                              │
│  CVAnalyzer - бизнес-логика анализа CV                     │
│  (использует RunnerClient)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Runner Client (Abstract)                   │
│  RunnerClient - базовый клиент для Runner API              │
│  - health_check()                                           │
│  - stream_request(endpoint, data) -> AsyncIterator         │
│  (в будущем можно заменить на другую реализацию)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  HHH Runner API                             │
│  http://155.212.245.141:8000                               │
│  - GET  /health                                             │
│  - POST /analyze-cv (SSE stream)                           │
│  - POST /... (будущие эндпоинты)                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Структура файлов

```
backend/src/
├── bot/
│   ├── handlers/
│   │   └── cv.py                 # Handler для /cv
│   └── states/
│       └── cv.py                 # FSM состояния
├── services/
│   └── runner/
│       ├── __init__.py           # Экспорт + фабрика get_runner_client()
│       ├── client.py             # RunnerClient (базовый клиент)
│       ├── cv_analyzer.py        # CVAnalyzer (анализ CV)
│       └── models.py             # StreamMessage, CVFile и др.
└── core/
    └── config.py                 # Настройки runner
```

---

## 3. Runner Client (базовый клиент)

### 3.1 client.py

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
import aiohttp
import asyncio

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
        user_id: int
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
        except Exception as e:
            return False, str(e)

    async def stream_request(
        self,
        endpoint: str,
        data: aiohttp.FormData,
        user_id: int
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

                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            import json
                            try:
                                msg = json.loads(line[6:])
                                yield StreamMessage(
                                    type=msg.get("type", "result"),
                                    content=msg.get("content", ""),
                                    metadata=msg.get("metadata")
                                )
                                if msg.get("type") == "done":
                                    return
                            except json.JSONDecodeError:
                                yield StreamMessage(type="result", content=line[6:])
        finally:
            self._cancel_flags.pop(user_id, None)

    async def cancel_stream(self, user_id: int) -> bool:
        if user_id in self._cancel_flags:
            self._cancel_flags[user_id].set()
            return True
        return False
```

### 3.2 models.py

```python
from dataclasses import dataclass
from enum import Enum


@dataclass
class StreamMessage:
    """Сообщение из SSE стрима Runner."""
    type: str  # "progress" | "result" | "error" | "done" | "cancelled"
    content: str
    metadata: dict | None = None


class FileValidationError(Enum):
    INVALID_FORMAT = "invalid_format"
    FILE_TOO_LARGE = "file_too_large"
    EMPTY_FILE = "empty_file"


@dataclass
class CVFile:
    """Валидированный файл CV."""
    content: bytes
    filename: str
    mime_type: str
    size: int

    MAX_SIZE = 1 * 1024 * 1024  # 1 MB
    ALLOWED_EXTENSIONS = {".pdf", ".txt"}

    @classmethod
    def validate(cls, content: bytes, filename: str, mime_type: str) -> "CVFile | FileValidationError":
        """Валидация файла CV."""
        if len(content) > cls.MAX_SIZE:
            return FileValidationError.FILE_TOO_LARGE

        if len(content) == 0:
            return FileValidationError.EMPTY_FILE

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in cls.ALLOWED_EXTENSIONS:
            return FileValidationError.INVALID_FORMAT

        return cls(
            content=content,
            filename=filename,
            mime_type=mime_type,
            size=len(content)
        )
```

---

## 4. CV Analyzer (бизнес-логика)

### 4.1 cv_analyzer.py

```python
from typing import AsyncIterator
import aiohttp

from .client import RunnerClient
from .models import StreamMessage, CVFile


class CVAnalyzer:
    """Сервис анализа CV через Runner."""

    ENDPOINT = "/analyze-cv"

    def __init__(self, runner: RunnerClient):
        self.runner = runner

    async def analyze(
        self,
        cv_file: CVFile,
        user_id: int
    ) -> AsyncIterator[StreamMessage]:
        """Запустить анализ CV."""
        form = aiohttp.FormData()
        form.add_field(
            "file",
            cv_file.content,
            filename=cv_file.filename,
            content_type=cv_file.mime_type
        )
        form.add_field("user_id", str(user_id))

        async for message in self.runner.stream_request(self.ENDPOINT, form, user_id):
            yield message

    async def cancel(self, user_id: int) -> bool:
        """Отменить анализ."""
        return await self.runner.cancel_stream(user_id)
```

---

## 5. Bot Handler

### 5.1 FSM States (states/cv.py)

```python
from aiogram.fsm.state import State, StatesGroup

class CVStates(StatesGroup):
    """Состояния для процесса анализа CV."""
    waiting_for_file = State()      # Ожидаем файл от пользователя
    processing = State()            # Анализ в процессе
```

### 5.2 Handler (handlers/cv.py)

```python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Document

from src.bot.states.cv import CVStates
from src.services.runner import get_cv_analyzer
from src.services.runner.models import CVFile, FileValidationError

router = Router(name="cv")

UPLOAD_PROMPT = """
📄 <b>Анализ CV</b>

Загрузите ваше резюме в формате <b>PDF</b> или <b>TXT</b>.

⚠️ Максимальный размер файла: <b>1 МБ</b>

Отправьте файл прямо в этот чат.
"""

ERROR_MESSAGES = {
    FileValidationError.INVALID_FORMAT: "❌ Неверный формат файла. Поддерживаются только PDF и TXT.",
    FileValidationError.FILE_TOO_LARGE: "❌ Файл слишком большой. Максимум 1 МБ.",
    FileValidationError.EMPTY_FILE: "❌ Файл пустой.",
}


@router.message(Command("cv"))
async def cmd_cv(message: Message, state: FSMContext) -> None:
    """Запуск команды анализа CV."""
    # Отменяем предыдущий анализ, если был
    analyzer = get_cv_analyzer()
    await analyzer.cancel(message.from_user.id)

    await state.set_state(CVStates.waiting_for_file)
    await message.answer(UPLOAD_PROMPT)


@router.message(CVStates.waiting_for_file, F.document)
async def handle_cv_file(message: Message, state: FSMContext) -> None:
    """Обработка загруженного файла CV."""
    document: Document = message.document

    # Скачиваем файл
    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)
    content = file_content.read()

    # Валидация
    result = CVFile.validate(content, document.file_name, document.mime_type)

    if isinstance(result, FileValidationError):
        await message.answer(ERROR_MESSAGES[result] + "\n\n" + UPLOAD_PROMPT)
        return

    cv_file: CVFile = result

    # Переходим в состояние обработки
    await state.set_state(CVStates.processing)
    await message.answer("🔄 Анализирую ваше резюме...")

    # Запускаем анализ
    analyzer = get_cv_analyzer()

    async for msg in analyzer.analyze(cv_file, message.from_user.id):
        if msg.type == "cancelled":
            break
        elif msg.type == "error":
            await message.answer(f"❌ {msg.content}")
            break
        elif msg.type == "done":
            await message.answer("✅ Анализ завершён!")
            break
        else:
            # Отправляем результат пользователю
            await message.answer(msg.content)

    await state.clear()


@router.message(CVStates.waiting_for_file)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода (текст вместо файла)."""
    await message.answer("❌ Пожалуйста, отправьте файл, а не текст.\n\n" + UPLOAD_PROMPT)
```

---

## 6. Отмена при смене команды

### 6.1 Middleware для отмены

При вызове любой другой команды автоматически отменять текущий анализ:

```python
# bot/middlewares/cancel_runner.py

from aiogram import BaseMiddleware
from aiogram.types import Message
from src.services.runner import get_runner_client

class CancelRunnerMiddleware(BaseMiddleware):
    """Отменяет активный стрим Runner при смене команды."""

    TRIGGER_COMMANDS = {"/start", "/help", "/profile", "/balance", "/tariffs", "/buy"}

    async def __call__(self, handler, event: Message, data: dict):
        if isinstance(event, Message) and event.text:
            if event.text.split()[0] in self.TRIGGER_COMMANDS:
                runner = get_runner_client()
                await runner.cancel_stream(event.from_user.id)

        return await handler(event, data)
```

---

## 7. Конфигурация

### 7.1 Переменные окружения

```env
# Runner service
RUNNER_BASE_URL=http://155.212.245.141:8000
RUNNER_API_KEY=runner-health-secret-key-2024
```

### 7.2 config.py дополнение

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Runner service
    runner_base_url: str = "http://155.212.245.141:8000"
    runner_api_key: str = "runner-health-secret-key-2024"
```

---

## 8. API Runner (ожидаемый контракт)

### 8.1 POST /analyze-cv

**Request:**
```
POST /analyze-cv
Content-Type: multipart/form-data
X-API-Key: runner-health-secret-key-2024

file: <binary>
user_id: 123456789
```

**Response (SSE stream):**
```
data: {"type": "progress", "content": "Читаю файл..."}

data: {"type": "result", "content": "## Анализ структуры\n\nВаше резюме содержит..."}

data: {"type": "result", "content": "## Рекомендации\n\n1. Добавьте..."}

data: {"type": "done", "content": ""}
```

**Типы сообщений:**
- `progress` — промежуточный статус
- `result` — часть результата анализа
- `error` — ошибка
- `done` — анализ завершён

---

## 9. User Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Пользователь: /enhancecv                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Бот: "Загрузите ваше резюме в формате PDF или TXT..."      │
│ [State: waiting_for_file]                                   │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    Текст/другое         PDF/TXT > 1MB      PDF/TXT ≤ 1MB
    "Отправьте файл"     "Файл слишком      │
                         большой"            ▼
                                   ┌─────────────────────────┐
                                   │ Бот: "Анализирую..."   │
                                   │ [State: processing]     │
                                   └─────────────────────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
                    Runner отвечает              Пользователь нажал
                    (SSE stream)                 другую команду
                              │                             │
                              ▼                             ▼
                    Бот отправляет              Анализ отменён
                    сообщения                   State cleared
                    пользователю
                              │
                              ▼
                    ┌─────────────────────────┐
                    │ "✅ Анализ завершён!"   │
                    │ [State: cleared]        │
                    └─────────────────────────┘
```

---

## 10. Замена реализации (в будущем)

Для замены Runner на другой сервис:

1. Создать новый класс, наследующий `BaseRunnerClient`
2. Изменить фабрику `get_runner_client()`:

```python
# services/runner/__init__.py

from src.core.config import settings
from .client import BaseRunnerClient, RunnerClient
from .cv_analyzer import CVAnalyzer

_runner: BaseRunnerClient | None = None
_cv_analyzer: CVAnalyzer | None = None


def get_runner_client() -> BaseRunnerClient:
    """Получить клиент Runner (singleton)."""
    global _runner
    if _runner is None:
        # Легко заменить на другую реализацию
        _runner = RunnerClient(
            base_url=settings.runner_base_url,
            api_key=settings.runner_api_key
        )
        # _runner = MockRunnerClient()  # для тестов
        # _runner = AlternativeRunnerClient()  # другая реализация
    return _runner


def get_cv_analyzer() -> CVAnalyzer:
    """Получить анализатор CV (singleton)."""
    global _cv_analyzer
    if _cv_analyzer is None:
        _cv_analyzer = CVAnalyzer(get_runner_client())
    return _cv_analyzer
```

---

## 11. Checklist реализации

- [ ] Создать `services/runner/models.py`
- [ ] Создать `services/runner/client.py`
- [ ] Создать `services/runner/cv_analyzer.py`
- [ ] Создать `services/runner/__init__.py` с фабриками
- [ ] Создать `bot/states/cv.py`
- [ ] Создать `bot/handlers/cv.py`
- [ ] Создать `bot/middlewares/cancel_runner.py`
- [ ] Добавить настройки в `core/config.py`
- [ ] Рефакторинг `healthcheck.py` — использовать `RunnerClient`
- [ ] Зарегистрировать handler в `main.py`
- [ ] Зарегистрировать middleware
- [ ] Добавить команду `/cv` в меню бота
- [ ] Тестирование
- [ ] Деплой

---

## 12. Открытые вопросы

1. **Формат ответов от Runner** — нужно уточнить точный формат SSE сообщений
2. **Таймауты** — какой максимальный таймаут для анализа?
3. **Очередь** — нужна ли очередь запросов или Runner обрабатывает параллельно?
4. **Персистентность** — сохранять ли историю анализов в БД?
5. **Лимиты** — есть ли лимит на количество анализов на пользователя?
