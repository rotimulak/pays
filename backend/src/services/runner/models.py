"""Models for Runner service."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class StreamMessage:
    """Сообщение из SSE стрима Runner."""

    type: str  # "progress" | "result" | "error" | "done" | "cancelled" | "complete"
    content: str
    metadata: dict | None = None
    task_id: str | None = None  # task_id для получения результата


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
