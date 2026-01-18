"""Skills analysis service with billing integration."""

import asyncio
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import BufferedInputFile

from src.core.exceptions import (
    InsufficientBalanceError,
    SubscriptionExpiredError,
)
from src.core.logging import get_logger
from src.services.runner import SkillsAnalyzer, BotOutputType, StreamMessage
from src.services.token_service import TokenService

logger = get_logger(__name__)

# Стоимость анализа навыков в токенах
SKILLS_COST = 1

# Лимит длины сообщения Telegram
MAX_MESSAGE_LENGTH = 4096

# Retry настройки
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # секунд


@dataclass
class SkillsResult:
    """Результат анализа навыков."""

    success: bool
    error: str | None = None
    tokens_spent: int = 0


class SkillsService:
    """Сервис анализа навыков на основе вакансий с интеграцией биллинга.

    Responsibilities:
    - Проверка права на использование (подписка, баланс)
    - Координация SkillsAnalyzer
    - Обработка bot_output событий
    - Списание токенов после успешного анализа
    """

    def __init__(
        self,
        token_service: TokenService,
        skills_analyzer: SkillsAnalyzer,
        bot: Bot,
    ):
        self.token_service = token_service
        self.skills_analyzer = skills_analyzer
        self.bot = bot

    async def check_access(self, user_id: int) -> tuple[bool, str | None]:
        """Проверить доступ пользователя к анализу навыков.

        Returns:
            (can_access, error_message)
        """
        return await self.token_service.can_spend(user_id, SKILLS_COST)

    async def analyze_skills(
        self,
        vacancy_urls: list[str],
        user_id: int,
        chat_id: int,
    ) -> SkillsResult:
        """Запустить анализ навыков по списку вакансий с биллингом.

        Flow:
        1. Проверить право на списание (подписка + баланс)
        2. Запустить анализ через SkillsAnalyzer
        3. Стримить результаты пользователю (включая bot_output)
        4. При успехе — списать токены

        Args:
            vacancy_urls: Список URL вакансий на hh.ru (до 20)
            user_id: Telegram user ID
            chat_id: Telegram chat ID для отправки сообщений

        Returns:
            SkillsResult с результатом операции
        """
        # 1. Проверка доступа
        can_spend, reason = await self.check_access(user_id)
        if not can_spend:
            return SkillsResult(success=False, error=reason)

        # 2. Запуск анализа
        success = False
        task_id: str | None = None

        try:
            async for message in self.skills_analyzer.analyze(vacancy_urls, user_id):
                result = await self._handle_stream_message(message, chat_id)

                if result == "error":
                    return SkillsResult(success=False, error=message.content)
                elif result == "cancelled":
                    return SkillsResult(success=False, error="Отменено")
                elif result == "complete":
                    success = True
                    task_id = message.task_id
                    break

        except Exception as e:
            logger.exception(f"Skills analysis failed: {e}")
            return SkillsResult(success=False, error=str(e))

        # 3. Списание токенов при успехе
        if success:
            try:
                await self.token_service.spend_tokens(
                    user_id=user_id,
                    amount=SKILLS_COST,
                    description="Анализ навыков",
                    metadata={"task_id": task_id, "vacancy_count": len(vacancy_urls)},
                )
                return SkillsResult(success=True, tokens_spent=SKILLS_COST)
            except (InsufficientBalanceError, SubscriptionExpiredError) as e:
                # Race condition: баланс изменился во время анализа
                logger.warning(f"Billing failed after skills analysis: {e}")
                return SkillsResult(
                    success=True,
                    tokens_spent=0,
                    error="Анализ завершён, но списание не удалось",
                )

        return SkillsResult(success=False, error="Анализ не завершён")

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
        """Обработать bot_output событие."""
        output = message.as_bot_output()
        if not output:
            logger.warning(f"Invalid bot_output: output_type={message.output_type}")
            return

        if output.output_type == BotOutputType.TEXT:
            if output.content:
                # Конвертируем format от Runner в parse_mode для Telegram
                parse_mode = "Markdown" if output.format == "markdown" else None
                await self._send_text_safe(chat_id, output.content, parse_mode=parse_mode)

        elif output.output_type == BotOutputType.FILE and output.content and output.filename:
            await self._send_document_safe(
                chat_id=chat_id,
                content=output.content,
                filename=output.filename,
                caption=output.caption,
            )

    async def _send_text_safe(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
    ) -> None:
        """Отправить текст, разбивая на части если нужно. С retry.

        Args:
            chat_id: ID чата
            text: Текст сообщения
            parse_mode: Режим парсинга ("Markdown", "MarkdownV2", "HTML" или None)
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            await self._send_with_retry(
                self.bot.send_message, chat_id, text, parse_mode=parse_mode
            )
        else:
            for i in range(0, len(text), MAX_MESSAGE_LENGTH):
                chunk = text[i : i + MAX_MESSAGE_LENGTH]
                await self._send_with_retry(
                    self.bot.send_message, chat_id, chunk, parse_mode=parse_mode
                )

    async def _send_document_safe(
        self,
        chat_id: int,
        content: str,
        filename: str,
        caption: str | None,
    ) -> None:
        """Отправить документ с retry."""
        file_bytes = content.encode("utf-8")
        await self._send_with_retry(
            self.bot.send_document,
            chat_id=chat_id,
            document=BufferedInputFile(file_bytes, filename),
            caption=caption,
        )

    async def _send_with_retry(self, method, *args, **kwargs) -> None:
        """Выполнить метод с retry при сетевых ошибках."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                await method(*args, **kwargs)
                return
            except TelegramNetworkError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"Telegram network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                    )
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Telegram network error after {MAX_RETRIES} attempts: {e}")

        if last_error:
            raise last_error

    async def cancel(self, user_id: int) -> bool:
        """Отменить текущий анализ навыков."""
        return await self.skills_analyzer.cancel(user_id)
