"""Models for Runner service."""

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
    {"type": "bot_output", "output_type": "file", "content": "...", "filename": "...", "caption": "..."}
    """

    output_type: BotOutputType
    content: str  # текст для TEXT, содержимое файла для FILE
    filename: str | None = None  # для FILE
    caption: str | None = None  # для FILE
    index: int | None = None  # порядковый номер события

    @classmethod
    def from_sse_data(cls, data: dict) -> "BotOutput | None":
        """Parse bot_output из SSE data."""
        output_type = data.get("output_type")
        if not output_type:
            return None

        try:
            return cls(
                output_type=BotOutputType(output_type),
                content=data.get("content", ""),
                filename=data.get("filename"),
                caption=data.get("caption"),
                index=data.get("index"),
            )
        except ValueError:
            return None


@dataclass
class StreamMessage:
    """Сообщение из SSE стрима Runner."""

    type: str  # progress | result | error | done | complete | cancelled | bot_output
    content: str
    metadata: dict | None = None
    task_id: str | None = None  # task_id для получения результата
    # Для bot_output — дополнительные поля
    output_type: str | None = None  # "text" | "file"
    filename: str | None = None
    caption: str | None = None

    def as_bot_output(self) -> BotOutput | None:
        """Parse as BotOutput if applicable."""
        if self.type != "bot_output" or not self.output_type:
            return None
        try:
            return BotOutput(
                output_type=BotOutputType(self.output_type),
                content=self.content,
                filename=self.filename,
                caption=self.caption,
            )
        except ValueError:
            return None


@dataclass
class TaskResult:
    """Результат выполнения задачи."""

    task_id: str
    status: str
    result_file: str | None
    content: str


class FileValidationError(Enum):
    """Ошибки валидации файла."""

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
            size=len(content),
        )
