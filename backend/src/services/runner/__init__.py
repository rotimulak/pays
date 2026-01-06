"""Runner service module."""

from src.core.config import settings

from .client import BaseRunnerClient, RunnerClient, TaskResponse
from .cv_analyzer import CVAnalyzer
from .models import CVFile, FileValidationError, StreamMessage, TaskResult

__all__ = [
    "BaseRunnerClient",
    "RunnerClient",
    "TaskResponse",
    "TaskResult",
    "CVAnalyzer",
    "CVFile",
    "FileValidationError",
    "StreamMessage",
    "get_runner_client",
    "get_cv_analyzer",
]

_runner: BaseRunnerClient | None = None
_cv_analyzer: CVAnalyzer | None = None


def get_runner_client() -> BaseRunnerClient:
    """Получить клиент Runner (singleton)."""
    global _runner
    if _runner is None:
        _runner = RunnerClient(
            base_url=settings.runner_base_url,
            api_key=settings.runner_api_key,
        )
    return _runner


def get_cv_analyzer() -> CVAnalyzer:
    """Получить анализатор CV (singleton)."""
    global _cv_analyzer
    if _cv_analyzer is None:
        _cv_analyzer = CVAnalyzer(get_runner_client())
    return _cv_analyzer
