"""Models for Runner service."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class TrackCost:
    """Track cost data from Runner Framework."""

    total_cost: float
    currency: str
    api_calls: int
    total_tokens: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    free_requests: int = 0
    node_costs: dict[str, float] | None = None


class BotOutputType(str, Enum):
    """Тип bot_output от Runner."""

    TEXT = "text"
    FILE = "file"


@dataclass
class BotOutput:
    """Parsed bot_output event.

    SSE format:
    {"type": "bot_output", "output_type": "text", "content": "...", "format": "markdown", "timestamp": "...", "index": 5}
    {"type": "bot_output", "output_type": "file", "content": "...", "filename": "...", "caption": "..."}
    """

    output_type: BotOutputType
    content: str  # текст для TEXT, содержимое файла для FILE
    filename: str | None = None  # для FILE
    caption: str | None = None  # для FILE
    index: int | None = None  # порядковый номер события
    format: str | None = None  # "markdown" | None - формат текста для TEXT

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
                format=data.get("format"),
            )
        except ValueError:
            return None


@dataclass
class StreamMessage:
    """Сообщение из SSE стрима Runner."""

    type: str  # progress | result | error | done | complete | cancelled | bot_output | track_cost
    content: str
    metadata: dict | None = None
    task_id: str | None = None  # task_id для получения результата
    # Для bot_output — дополнительные поля
    output_type: str | None = None  # "text" | "file"
    filename: str | None = None
    caption: str | None = None
    format: str | None = None  # "markdown" | None - формат текста
    # Для track_cost — raw data
    track_cost_data: dict | None = None

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
                format=self.format,
            )
        except ValueError:
            return None

    def as_track_cost(self) -> TrackCost | None:
        """Parse as TrackCost if applicable."""
        if self.type != "track_cost" or not self.track_cost_data:
            return None
        try:
            return TrackCost(
                total_cost=self.track_cost_data["total_cost"],
                currency=self.track_cost_data.get("currency", "RUB"),
                api_calls=self.track_cost_data.get("api_calls", 0),
                total_tokens=self.track_cost_data.get("total_tokens", 0),
                prompt_tokens=self.track_cost_data.get("prompt_tokens"),
                completion_tokens=self.track_cost_data.get("completion_tokens"),
                free_requests=self.track_cost_data.get("free_requests", 0),
                node_costs=self.track_cost_data.get("node_costs"),
            )
        except (KeyError, TypeError):
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
