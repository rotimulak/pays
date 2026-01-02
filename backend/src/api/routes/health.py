"""Health check endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str = "hhhelper-api"


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str
    database: str
    service: str = "hhhelper-api"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness probe.

    Returns 200 if the service is running.
    Used by Docker/Kubernetes to check if the container is alive.
    """
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(
    session: AsyncSession = Depends(get_session),
) -> ReadyResponse:
    """
    Readiness probe.

    Returns 200 if the service is ready to accept traffic.
    Checks database connectivity.
    """
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    status = "ok" if db_status == "connected" else "degraded"

    return ReadyResponse(status=status, database=db_status)
