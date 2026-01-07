# Bot Output - Implementation Spec v2

> **Status:** To Do
> **Priority:** High
> **Depends on:** Runner bot_output implementation

## Overview

Обработка SSE событий `bot_output` от Runner для отправки текста и файлов пользователю в реальном времени. Интеграция с системой биллинга (проверка подписки, списание токенов).

---

## SSE Events от Runner (Input)

### Типы событий

#### 1. Progress (существующие)
```
event: progress
data: {"type": "progress", "content": "Executing node...", "progress": 25}
```

#### 2. Bot output — text (НОВОЕ)
```
event: bot_output
data: {"type": "bot_output", "output_type": "text", "content": "Анализ завершен!", "timestamp": "...", "index": 5}
```

#### 3. Bot output — file (НОВОЕ)
```
event: bot_output
data: {"type": "bot_output", "output_type": "file", "content": "## Анализ...", "filename": "cv_analysis.txt", "caption": "Результат", "timestamp": "...", "index": 6}
```

#### 4. Complete/Done
```
event: complete
data: {"type": "complete", "status": "completed", "task_id": "abc-123"}
```

#### 5. Error
```
event: error
data: {"type": "error", "content": "Ошибка обработки файла"}
```

---

## Архитектура (соответствует проекту)

```
src/
├── bot/
│   ├── handlers/cv.py           # Координация: файл → сервис → ответ
│   └── states/cv.py             # FSM: waiting_for_file, processing
├── services/
│   ├── runner/
│   │   ├── client.py            # RunnerClient (HTTP + SSE)
│   │   ├── cv_analyzer.py       # CVAnalyzer (координация Runner)
│   │   └── models.py            # StreamMessage, CVFile, BotOutput
│   ├── cv_service.py            # НОВЫЙ: бизнес-логика + биллинг
│   └── token_service.py         # Списание токенов
└── core/
    └── exceptions.py            # SubscriptionExpiredError, etc.
```

**Поток данных:**
```
Handler (cv.py)
    │
    ▼
CVService (cv_service.py)        ← НОВЫЙ слой
    ├── TokenService.can_spend() — проверка права
    ├── CVAnalyzer.analyze()     — запуск Runner
    ├── _handle_bot_output()     — обработка bot_output
    └── TokenService.spend()     — списание после успеха
    │
    ▼
RunnerClient (client.py)
    │
    ▼
Runner API (SSE stream)
```

---

## Изменения в models.py

```python
# services/runner/models.py

from dataclasses import dataclass
from enum import Enum


class BotOutputType(str, Enum):
    """Тип bot_output от Runner."""
    TEXT = "text"
    FILE = "file"


@dataclass
class BotOutput:
    """Parsed bot_output event.

    SSE format:
    {"type": "bot_output", "output_type": "text", "content": "...", "timestamp": "...", "index": 5}
    {"type": "bot_output", "output_type": "file", "content": "...", "filename": "...", "caption": "...", ...}
    """
    output_type: BotOutputType
    content: str                     # текст для TEXT, содержимое файла для FILE
    filename: str | None = None      # для FILE
    caption: str | None = None       # для FILE
    index: int | None = None         # порядковый номер события

    @classmethod
    def from_sse_data(cls, data: dict) -> "BotOutput | None":
        """Parse bot_output из SSE data."""
        output_type = data.get("output_type")
        if not output_type:
            return None

        return cls(
            output_type=BotOutputType(output_type),
            content=data.get("content", ""),
            filename=data.get("filename"),
            caption=data.get("caption"),
            index=data.get("index"),
        )


@dataclass
class StreamMessage:
    """Сообщение из SSE стрима Runner."""
    type: str  # progress | result | error | done | complete | cancelled | bot_output
    content: str
    metadata: dict | None = None
    task_id: str | None = None
    # Для bot_output — дополнительные поля
    output_type: str | None = None   # "text" | "file"
    filename: str | None = None
    caption: str | None = None

    def as_bot_output(self) -> BotOutput | None:
        """Parse as BotOutput if applicable."""
        if self.type != "bot_output" or not self.output_type:
            return None
        return BotOutput(
            output_type=BotOutputType(self.output_type),
            content=self.content,
            filename=self.filename,
            caption=self.caption,
        )
```

---

## Новый сервис: CVService

```python
# services/cv_service.py

"""CV analysis service with billing integration."""

import io
from dataclasses import dataclass
from typing import AsyncIterator

from aiogram import Bot
from aiogram.types import BufferedInputFile

from src.core.exceptions import (
    InsufficientBalanceError,
    SubscriptionExpiredError,
    UserBlockedError,
)
from src.core.logging import get_logger
from src.db.repositories.user_repository import UserRepository
from src.services.runner import CVAnalyzer, CVFile, StreamMessage, BotOutput, BotOutputType
from src.services.token_service import TokenService

logger = get_logger(__name__)

# Стоимость анализа CV в токенах
CV_ANALYSIS_COST = 1


@dataclass
class CVAnalysisResult:
    """Результат анализа CV."""
    success: bool
    error: str | None = None
    tokens_spent: int = 0


class CVService:
    """Сервис анализа CV с интеграцией биллинга.

    Responsibilities:
    - Проверка права на использование (подписка, баланс)
    - Координация CVAnalyzer
    - Обработка bot_output событий
    - Списание токенов после успешного анализа
    """

    def __init__(
        self,
        token_service: TokenService,
        cv_analyzer: CVAnalyzer,
        bot: Bot,
    ):
        self.token_service = token_service
        self.cv_analyzer = cv_analyzer
        self.bot = bot

    async def check_access(self, user_id: int) -> tuple[bool, str | None]:
        """Проверить доступ пользователя к анализу CV.

        Returns:
            (can_access, error_message)
        """
        return await self.token_service.can_spend(user_id, CV_ANALYSIS_COST)

    async def analyze_cv(
        self,
        cv_file: CVFile,
        user_id: int,
        chat_id: int,
    ) -> CVAnalysisResult:
        """Запустить анализ CV с биллингом.

        Flow:
        1. Проверить право на списание (подписка + баланс)
        2. Запустить анализ через CVAnalyzer
        3. Стримить результаты пользователю (включая bot_output)
        4. При успехе — списать токены

        Args:
            cv_file: Валидированный файл CV
            user_id: Telegram user ID
            chat_id: Telegram chat ID для отправки сообщений

        Returns:
            CVAnalysisResult с результатом операции
        """
        # 1. Проверка доступа
        can_spend, reason = await self.check_access(user_id)
        if not can_spend:
            return CVAnalysisResult(success=False, error=reason)

        # 2. Запуск анализа
        success = False
        task_id: str | None = None

        try:
            async for message in self.cv_analyzer.analyze(cv_file, user_id):
                result = await self._handle_stream_message(message, chat_id)

                if result == "error":
                    return CVAnalysisResult(success=False, error=message.content)
                elif result == "cancelled":
                    return CVAnalysisResult(success=False, error="Отменено")
                elif result == "complete":
                    success = True
                    task_id = message.task_id
                    break

        except Exception as e:
            logger.exception(f"CV analysis failed: {e}")
            return CVAnalysisResult(success=False, error=str(e))

        # 3. Списание токенов при успехе
        if success:
            try:
                await self.token_service.spend_tokens(
                    user_id=user_id,
                    amount=CV_ANALYSIS_COST,
                    description="Анализ CV",
                    idempotency_key=f"cv_analysis_{task_id}" if task_id else None,
                    metadata={"task_id": task_id},
                )
                return CVAnalysisResult(success=True, tokens_spent=CV_ANALYSIS_COST)
            except (InsufficientBalanceError, SubscriptionExpiredError) as e:
                # Race condition: баланс изменился во время анализа
                logger.warning(f"Billing failed after analysis: {e}")
                return CVAnalysisResult(success=True, tokens_spent=0, error="Анализ выполнен, но списание не удалось")

        return CVAnalysisResult(success=False, error="Анализ не завершён")

    async def _handle_stream_message(
        self,
        message: StreamMessage,
        chat_id: int,
    ) -> str:
        """Обработать сообщение из стрима.

        Returns:
            "continue" | "error" | "cancelled" | "complete"
        """
        if message.type == "cancelled":
            return "cancelled"

        if message.type == "error":
            await self.bot.send_message(chat_id, f"❌ {message.content}")
            return "error"

        if message.type in ("done", "complete"):
            return "complete"

        if message.type == "progress":
            # Пропускаем технические прогресс-сообщения
            return "continue"

        if message.type == "bot_output":
            await self._handle_bot_output(message, chat_id)
            return "continue"

        if message.type == "result" and message.content:
            # Legacy: текстовый результат
            await self._send_text_safe(chat_id, message.content)
            return "continue"

        return "continue"

    async def _handle_bot_output(
        self,
        message: StreamMessage,
        chat_id: int,
    ) -> None:
        """Обработать bot_output событие.

        SSE format:
        - text: {"output_type": "text", "content": "Текст сообщения"}
        - file: {"output_type": "file", "content": "содержимое", "filename": "...", "caption": "..."}
        """
        output = message.as_bot_output()
        if not output:
            logger.warning(f"Invalid bot_output: output_type={message.output_type}")
            return

        if output.output_type == BotOutputType.TEXT:
            if output.content:
                await self._send_text_safe(chat_id, output.content)

        elif output.output_type == BotOutputType.FILE:
            if output.content and output.filename:
                file_bytes = output.content.encode("utf-8")
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=BufferedInputFile(file_bytes, output.filename),
                    caption=output.caption,
                )

    async def _send_text_safe(self, chat_id: int, text: str) -> None:
        """Отправить текст, разбивая на части если нужно."""
        MAX_LENGTH = 4096

        if len(text) <= MAX_LENGTH:
            await self.bot.send_message(chat_id, text)
        else:
            for i in range(0, len(text), MAX_LENGTH):
                chunk = text[i:i + MAX_LENGTH]
                await self.bot.send_message(chat_id, chunk)

    async def cancel(self, user_id: int) -> bool:
        """Отменить текущий анализ."""
        return await self.cv_analyzer.cancel(user_id)
```

---

## Обновлённый handler

```python
# bot/handlers/cv.py

"""CV analysis command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Document, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.cv import CVStates
from src.core.logging import get_logger
from src.services.cv_service import CVService, CV_ANALYSIS_COST
from src.services.runner import CVFile, FileValidationError, get_cv_analyzer
from src.services.token_service import TokenService

logger = get_logger(__name__)

router = Router(name="cv")

UPLOAD_PROMPT = """
📄 <b>Анализ CV</b>

Загрузите ваше резюме в формате <b>PDF</b> или <b>TXT</b>.

⚠️ Максимальный размер файла: <b>1 МБ</b>
💰 Стоимость: <b>{cost} токен</b>

Отправьте файл прямо в этот чат.
""".strip()

ERROR_MESSAGES = {
    FileValidationError.INVALID_FORMAT: "❌ Неверный формат файла. Поддерживаются только PDF и TXT.",
    FileValidationError.FILE_TOO_LARGE: "❌ Файл слишком большой. Максимум 1 МБ.",
    FileValidationError.EMPTY_FILE: "❌ Файл пустой.",
}


def _get_cv_service(session: AsyncSession, bot) -> CVService:
    """Factory для CVService с DI."""
    return CVService(
        token_service=TokenService(session),
        cv_analyzer=get_cv_analyzer(),
        bot=bot,
    )


@router.message(Command("cv"))
async def cmd_cv(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Запуск команды анализа CV."""
    cv_service = _get_cv_service(session, message.bot)

    # Отменяем предыдущий анализ
    await cv_service.cancel(message.from_user.id)

    # Проверяем доступ до показа промпта
    can_access, reason = await cv_service.check_access(message.from_user.id)
    if not can_access:
        await message.answer(f"❌ {reason}\n\nИспользуйте /buy для пополнения.")
        return

    await state.set_state(CVStates.waiting_for_file)
    await message.answer(UPLOAD_PROMPT.format(cost=CV_ANALYSIS_COST))


@router.message(CVStates.waiting_for_file, F.document)
async def handle_cv_file(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка загруженного файла CV."""
    document: Document = message.document

    # Скачиваем и валидируем файл
    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)
    content = file_content.read()

    result = CVFile.validate(content, document.file_name or "file", document.mime_type or "")

    if isinstance(result, FileValidationError):
        await message.answer(ERROR_MESSAGES[result])
        return

    cv_file: CVFile = result

    # Переходим в состояние обработки
    await state.set_state(CVStates.processing)
    await message.answer("🔄 Анализирую ваше резюме...")

    # Запускаем анализ через сервис
    cv_service = _get_cv_service(session, message.bot)
    analysis_result = await cv_service.analyze_cv(
        cv_file=cv_file,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    # Завершаем
    if analysis_result.success:
        if analysis_result.tokens_spent > 0:
            await message.answer(f"✅ Анализ завершён! Списано: {analysis_result.tokens_spent} токен")
        else:
            await message.answer("✅ Анализ завершён!")
    elif analysis_result.error:
        # Ошибка уже отправлена в _handle_stream_message
        pass

    await state.clear()


@router.message(CVStates.waiting_for_file)
async def handle_invalid_input(message: Message) -> None:
    """Обработка невалидного ввода."""
    await message.answer(f"❌ Пожалуйста, отправьте файл.\n\n{UPLOAD_PROMPT.format(cost=CV_ANALYSIS_COST)}")
```

---

## Изменения в client.py

Добавить обработку `bot_output` типа в `stream_task`:

```python
# В методе stream_task, после парсинга JSON (строка ~176):

msg_type = msg.get("type", "result")
msg_content = msg.get("content", "")

# Поддержка bot_output
if msg_type == "bot_output":
    yield StreamMessage(
        type="bot_output",
        content=msg_content,
        output_type=msg.get("output_type"),  # "text" | "file"
        filename=msg.get("filename"),
        caption=msg.get("caption"),
    )
    continue

# Остальная логика...
```

Полный diff для `stream_task`:

```python
# После строки: msg_content = msg.get("content", "")

if msg_type == "error" and not msg_content:
    msg_content = "Неизвестная ошибка сервера"

# NEW: Handle bot_output
if msg_type == "bot_output":
    yield StreamMessage(
        type="bot_output",
        content=msg_content,
        output_type=msg.get("output_type"),
        filename=msg.get("filename"),
        caption=msg.get("caption"),
    )
    continue

# Передаём task_id в complete/done сообщениях
yield StreamMessage(
    type=msg_type,
    content=msg_content,
    metadata=msg.get("metadata"),
    task_id=task_id if msg_type in ("done", "complete") else None,
)
```

---

## Порядок сообщений пользователю

При обработке CV пользователь получит:

1. `"🔄 Анализирую ваше резюме..."` — после загрузки файла
2. `[bot_output: text]` — "CV успешно прочитано. Начинаю анализ..."
3. `[bot_output: text]` — "Анализ завершен. Отправляю результат..."
4. `[bot_output: file]` — cv_analysis.md с caption
5. `[bot_output: file]` — recommendations.md (опционально)
6. `"✅ Анализ завершён! Списано: 1 токен"` — при complete

---

## Обработка ошибок

| Ошибка | Когда | Сообщение пользователю |
|--------|-------|------------------------|
| `SubscriptionExpiredError` | До анализа | "Подписка истекла. Используйте /buy" |
| `InsufficientBalanceError` | До анализа | "Недостаточно токенов. Используйте /buy" |
| `UserBlockedError` | До анализа | "Аккаунт заблокирован" |
| `FileValidationError` | При загрузке | "Неверный формат / слишком большой / пустой" |
| SSE error | Во время анализа | "❌ {error_content}" |
| Timeout | Во время анализа | "❌ Ошибка соединения: TimeoutError" |

---

## Идемпотентность

- `idempotency_key` для транзакции: `cv_analysis_{task_id}`
- Повторный webhook с тем же task_id → транзакция не дублируется
- Если пользователь отправит файл дважды → два разных task_id → два списания

---

## Тестирование

### Unit tests

```python
# tests/services/test_cv_service.py

async def test_analyze_cv_checks_access_first():
    """CVService должен проверить доступ до запуска анализа."""
    ...

async def test_analyze_cv_spends_tokens_on_success():
    """Токены списываются только при успешном анализе."""
    ...

async def test_analyze_cv_no_spend_on_error():
    """Токены НЕ списываются при ошибке."""
    ...

async def test_bot_output_text_sent_to_user():
    """bot_output с type=text отправляется как сообщение."""
    ...

async def test_bot_output_file_sent_as_document():
    """bot_output с type=file отправляется как документ."""
    ...
```

### Integration tests

1. Отправить PDF файл боту
2. Проверить что сообщения приходят по мере выполнения
3. Проверить что файлы корректно открываются
4. Проверить списание токена в transactions
5. Проверить баланс пользователя после анализа

---

## Checklist

### Код
- [ ] Добавить `BotOutput` в models.py
- [ ] Создать `CVService` в services/cv_service.py
- [ ] Обновить handler в bot/handlers/cv.py
- [ ] Добавить обработку `bot_output` в client.py
- [ ] `mypy --strict`
- [ ] `ruff check && ruff format`

### Биллинг
- [ ] Проверка подписки перед анализом
- [ ] Проверка баланса перед анализом
- [ ] Списание токенов после успеха
- [ ] Idempotency key для транзакции

### Тесты
- [ ] Unit tests для CVService
- [ ] Integration test: полный flow с биллингом

### Production
- [ ] Логирование всех этапов
- [ ] Graceful handling ошибок Runner
- [ ] Отмена анализа при /cv повторно
