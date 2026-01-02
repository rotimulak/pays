"""Rate limiting middleware."""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    For production, consider using Redis-based solution.
    """

    def __init__(self, app, calls: int = 100, period: int = 60) -> None:
        """Initialize rate limiter.

        Args:
            app: FastAPI/Starlette application
            calls: Max calls per period
            period: Period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests: dict[str, list[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        async with self._lock:
            if not self._is_allowed(client_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limited",
                        "message": f"Too many requests. Limit: {self.calls} per {self.period}s",
                        "retry_after": self.period,
                    },
                    headers={"Retry-After": str(self.period)},
                )

            self._record_request(client_id)

        return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting.

        Priority:
        1. API key from Authorization header
        2. X-Forwarded-For header (for proxied requests)
        3. Client IP address
        """
        # Prefer API key if present
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return f"key:{auth[7:]}"

        # Check X-Forwarded-For for proxied requests
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        # Fall back to client IP
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _is_allowed(self, client_id: str) -> bool:
        """Check if request is within rate limit."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.period)

        # Clean old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id] if t > cutoff
        ]

        return len(self.requests[client_id]) < self.calls

    def _record_request(self, client_id: str) -> None:
        """Record new request."""
        self.requests[client_id].append(datetime.utcnow())

    def reset(self) -> None:
        """Clear all rate limit data. Useful for testing."""
        self.requests.clear()
