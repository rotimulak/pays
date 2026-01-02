"""API module."""

from fastapi import FastAPI

from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routes import health, tokens, webhook
from src.core.config import settings
from src.payments.providers.mock.router import router as mock_payment_router


def create_api() -> FastAPI:
    """Create FastAPI application for webhooks and token API."""
    app = FastAPI(
        title="Telegram Billing API",
        description="Webhook handlers and Token API for payment processing",
        version="1.0.0",
    )

    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        calls=settings.rate_limit_calls,
        period=settings.rate_limit_period,
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(webhook.router)
    app.include_router(tokens.router)
    app.include_router(mock_payment_router)

    return app


__all__ = ["create_api"]
