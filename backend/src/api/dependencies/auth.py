"""API authentication dependencies."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.core.config import settings

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Verify API key from Authorization header.

    Expected format: Bearer {api_key}

    Args:
        api_key: Value from Authorization header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer {token}"
    if api_key.startswith("Bearer "):
        token = api_key[7:]
    else:
        token = api_key

    if token != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
