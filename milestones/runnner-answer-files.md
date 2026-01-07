# Bot Output - Bot Implementation Spec

> **Status:** To Do
> **Priority:** High
> **Depends on:** Runner bot_output implementation

## Overview

Обработка SSE событий `bot_output` от Runner для отправки текста и файлов пользователю в реальном времени по мере выполнения трека.

## SSE Events от Runner

### Типы событий

#### 1. Progress events (существующие)

```
event: progress
data: {"type": "progress", "message": "Executing node...", "progress": 25}
```

#### 2. Bot output - text

```
event: message
data: {"type": "bot_output", "output_type": "text", "content": "Анализ завершен!", "timestamp": "..."}
```

#### 3. Bot output - file

```
event: message
data: {"type": "bot_output", "output_type": "file", "filename": "analysis.md", "content": "## Анализ...", "caption": "Результат анализа", "timestamp": "..."}
```

#### 4. Complete event

```
event: complete
data: {"status": "completed", "result_file": "path/to/file"}
```

## Логика обработки SSE

```python
import httpx
import io
from telegram import Update

async def process_cv_stream(task_id: str, chat_id: int, bot):
    """Process SSE stream from Runner and send messages to user."""

    url = f"{RUNNER_URL}/api/tasks/{task_id}/stream"
    headers = {"X-API-Key": HEALTH_API_KEY}

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("GET", url, headers=headers) as response:
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                # Parse SSE data
                json_str = line[5:].strip()  # Remove "data:" prefix
                if not json_str:
                    continue

                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    continue

                # Handle different message types
                msg_type = data.get("type")

                if msg_type == "bot_output":
                    await handle_bot_output(data, chat_id, bot)

                elif msg_type == "progress":
                    # Optional: show progress updates
                    pass

                elif data.get("status") == "completed":
                    # Stream finished successfully
                    break

                elif data.get("error"):
                    # Error occurred
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"Ошибка: {data.get('error')}"
                    )
                    break


async def handle_bot_output(data: dict, chat_id: int, bot):
    """Handle bot_output message from Runner."""

    output_type = data.get("output_type")

    if output_type == "text":
        # Send text message
        content = data.get("content", "")
        if content:
            await bot.send_message(
                chat_id=chat_id,
                text=content,
                parse_mode="Markdown"
            )

    elif output_type == "file":
        # Send file as document
        content = data.get("content", "")
        filename = data.get("filename", "result.md")
        caption = data.get("caption", "")

        if content:
            file_bytes = content.encode("utf-8")
            await bot.send_document(
                chat_id=chat_id,
                document=io.BytesIO(file_bytes),
                filename=filename,
                caption=caption if caption else None
            )
```

## Полный пример обработки CV

```python
from telegram import Update
from telegram.ext import ContextTypes
import httpx
import asyncio
import json
import io

RUNNER_URL = "http://155.212.245.141:8000"
HEALTH_API_KEY = os.getenv("HEALTH_API_KEY", "")


async def handle_cv_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CV file upload from user."""

    # 1. Get file from Telegram
    document = update.message.document
    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()

    # 2. Send to Runner
    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": (document.file_name, bytes(file_bytes))}
        data = {"telegram_id": str(update.effective_user.id)}
        headers = {"X-API-Key": HEALTH_API_KEY}

        response = await client.post(
            f"{RUNNER_URL}/analyze-cv",
            files=files,
            data=data,
            headers=headers
        )

        if response.status_code != 200:
            await update.message.reply_text("Ошибка загрузки файла")
            return

        result = response.json()
        task_id = result["task_id"]

    # 3. Send initial message
    await update.message.reply_text(
        f"Файл получен. Анализирую...\n"
        f"Позиция в очереди: {result.get('queue_position', 1)}"
    )

    # 4. Process SSE stream
    await process_cv_stream(
        task_id=task_id,
        chat_id=update.effective_chat.id,
        bot=context.bot
    )


async def process_cv_stream(task_id: str, chat_id: int, bot):
    """Process SSE stream and send updates to user."""

    url = f"{RUNNER_URL}/api/tasks/{task_id}/stream"
    headers = {"X-API-Key": HEALTH_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("GET", url, headers=headers) as response:
                event_type = None

                async for line in response.aiter_lines():
                    line = line.strip()

                    # Parse SSE format
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                        continue

                    if not line.startswith("data:"):
                        continue

                    json_str = line[5:].strip()
                    if not json_str:
                        continue

                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue

                    # Handle bot_output
                    if data.get("type") == "bot_output":
                        output_type = data.get("output_type")

                        if output_type == "text":
                            await bot.send_message(
                                chat_id=chat_id,
                                text=data.get("content", ""),
                                parse_mode="Markdown"
                            )

                        elif output_type == "file":
                            content = data.get("content", "")
                            filename = data.get("filename", "result.md")
                            caption = data.get("caption")

                            await bot.send_document(
                                chat_id=chat_id,
                                document=io.BytesIO(content.encode("utf-8")),
                                filename=filename,
                                caption=caption
                            )

                    # Handle completion
                    elif event_type == "complete" or data.get("status") == "completed":
                        await bot.send_message(
                            chat_id=chat_id,
                            text="Обработка завершена!"
                        )
                        break

                    # Handle error
                    elif event_type == "error" or data.get("error"):
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"Ошибка: {data.get('error', 'Unknown error')}"
                        )
                        break

    except httpx.TimeoutException:
        await bot.send_message(
            chat_id=chat_id,
            text="Превышено время ожидания. Попробуйте позже."
        )
    except Exception as e:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Ошибка подключения: {str(e)}"
        )
```

## Порядок сообщений пользователю

При обработке CV пользователь получит:

1. "Файл получен. Анализирую..." (сразу после загрузки)
2. "CV успешно прочитано. Начинаю анализ..." (после extract_text)
3. "Анализ завершен. Отправляю результат..." (после analyze_cv)
4. [Файл: cv_analysis.md] (после analyze_cv)
5. [Файл: recommendations.md] (после generate_recommendations)
6. "Готово! Вот ваш конструктор CV:" (после build_constructor)
7. [Файл: cv_constructor.md] (после build_constructor)
8. "Обработка завершена!" (при получении complete)

## Зависимости

```
httpx>=0.27.0
python-telegram-bot>=22.0
```

## Тестирование

1. Отправить PDF файл боту
2. Проверить что сообщения приходят по мере выполнения
3. Проверить что файлы корректно открываются
4. Проверить обработку ошибок (таймаут, неверный формат)

## Fallback (если SSE не работает)

Если SSE недоступен, использовать polling:

```python
async def poll_task_result(task_id: str, chat_id: int, bot):
    """Fallback: poll task status instead of SSE."""

    url = f"{RUNNER_URL}/api/tasks/{task_id}"
    headers = {"X-API-Key": HEALTH_API_KEY}

    async with httpx.AsyncClient() as client:
        for _ in range(120):  # Max 2 minutes
            response = await client.get(url, headers=headers)
            data = response.json()

            if data["status"] == "completed":
                # Get result
                result_response = await client.get(
                    f"{RUNNER_URL}/api/tasks/{task_id}/result",
                    headers=headers
                )
                result = result_response.json()

                await bot.send_document(
                    chat_id=chat_id,
                    document=io.BytesIO(result["content"].encode()),
                    filename="cv_result.md"
                )
                return

            elif data["status"] == "failed":
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"Ошибка: {data.get('error')}"
                )
                return

            await asyncio.sleep(1)

    await bot.send_message(
        chat_id=chat_id,
        text="Превышено время ожидания"
    )
```
