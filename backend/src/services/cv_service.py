"""CV analysis service with billing integration."""

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
from src.services.runner import BotOutputType, CVAnalyzer, CVFile, StreamMessage
from src.services.token_service import TokenService

logger = get_logger(__name__)

# Стоимость анализа CV в токенах (fallback если Runner не отправил track_cost)
CV_ANALYSIS_FALLBACK_COST = 1

# Лимит длины сообщения Telegram
MAX_MESSAGE_LENGTH = 4096

# Retry настройки
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # секунд


@dataclass
class CVAnalysisResult:
    """Результат анализа CV."""

    success: bool
    error: str | None = None
    tokens_spent: float = 0.0


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
        self._track_cost: float | None = None  # Стоимость текущего трека

    async def check_access(self, user_id: int) -> tuple[bool, str | None]:
        """Проверить доступ пользователя к анализу CV.

        Returns:
            (can_access, error_message)
        """
        # Проверяем только подписку и блокировку, не баланс
        balance = await self.token_service.check_balance(user_id)
        return balance.can_spend, balance.reason

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
            from src.core.config import settings

            # Списываем фактическую стоимость из track_cost
            # Fallback на фиксированную стоимость, если Runner не отправил track_cost
            if self._track_cost is None:
                logger.warning(
                    f"Track completed without cost data, using fallback cost: {CV_ANALYSIS_FALLBACK_COST}"
                )
                self._track_cost = CV_ANALYSIS_FALLBACK_COST
                # Для fallback не применяем multiplier, используем прямое значение
                final_cost = float(CV_ANALYSIS_FALLBACK_COST)
                multiplier_used = 1.0
            else:
                # Применяем мультипликатор для динамической стоимости от Runner
                final_cost = self._track_cost * settings.cost_multiplier
                multiplier_used = settings.cost_multiplier

            # Округляем до 2 знаков
            final_cost = round(final_cost, 2)

            logger.info(
                f"Charging user: raw_cost={self._track_cost}, "
                f"multiplier={multiplier_used}, final_cost={final_cost}"
            )

            try:
                await self.token_service.spend_tokens(
                    user_id=user_id,
                    amount=final_cost,
                    description="Анализ CV",
                    metadata={
                        "task_id": task_id,
                        "cost_raw": self._track_cost,
                        "cost_multiplier": settings.cost_multiplier,
                        "cost_final": final_cost,
                    },
                )

                # Сбросить стоимость для следующего запуска
                self._track_cost = None

                return CVAnalysisResult(success=True, tokens_spent=final_cost)
            except Exception as e:
                # Разрешаем минус, логируем ошибку
                logger.warning(f"Billing failed after analysis: {e}")
                self._track_cost = None
                return CVAnalysisResult(
                    success=True,
                    tokens_spent=0,
                    error="Анализ выполнен, но списание не удалось",
                )

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

        if message.type == "track_cost":
            cost_data = message.as_track_cost()
            if cost_data:
                self._track_cost = cost_data.total_cost
                logger.info(f"Track cost received: {cost_data.total_cost} {cost_data.currency}")
            return "continue"

        if message.type in ("done", "complete"):
            return "complete"

        if message.type == "progress":
            # Пропускаем технические прогресс-сообщения
            return "continue"

        if message.type == "bot_output":
            # Проверяем track_cost, который приходит как bot_output с output_type="track_cost"
            if message.output_type == "track_cost" and message.metadata:
                self._track_cost = message.metadata.get("total_cost")
                if self._track_cost:
                    currency = message.metadata.get("currency", "RUB")
                    logger.info(f"Track cost received (via bot_output): {self._track_cost} {currency}")
                return "continue"

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
        """Отменить текущий анализ."""
        return await self.cv_analyzer.cancel(user_id)
