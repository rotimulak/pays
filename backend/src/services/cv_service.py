"""CV analysis service with billing integration."""

from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import BufferedInputFile

from src.core.exceptions import (
    InsufficientBalanceError,
    SubscriptionExpiredError,
)
from src.core.logging import get_logger
from src.services.runner import BotOutputType, CVAnalyzer, CVFile, StreamMessage
from src.services.token_service import TokenService

logger = get_logger(__name__)

# Стоимость анализа CV в токенах
CV_ANALYSIS_COST = 1

# Лимит длины сообщения Telegram
MAX_MESSAGE_LENGTH = 4096


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

        elif output.output_type == BotOutputType.FILE and output.content and output.filename:
            file_bytes = output.content.encode("utf-8")
            await self.bot.send_document(
                chat_id=chat_id,
                document=BufferedInputFile(file_bytes, output.filename),
                caption=output.caption,
            )

    async def _send_text_safe(self, chat_id: int, text: str) -> None:
        """Отправить текст, разбивая на части если нужно."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            await self.bot.send_message(chat_id, text)
        else:
            for i in range(0, len(text), MAX_MESSAGE_LENGTH):
                chunk = text[i : i + MAX_MESSAGE_LENGTH]
                await self.bot.send_message(chat_id, chunk)

    async def cancel(self, user_id: int) -> bool:
        """Отменить текущий анализ."""
        return await self.cv_analyzer.cancel(user_id)
