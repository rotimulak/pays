"""API module."""

from fastapi import FastAPI

from src.api.routes import webhook
from src.payments.providers.mock.router import router as mock_payment_router


def create_api() -> FastAPI:
    """Create FastAPI application for webhooks and mock payment."""
    app = FastAPI(
        title="Telegram Billing API",
        description="Webhook handlers for payment processing",
        version="1.0.0",
    )

    # Include routers
    app.include_router(webhook.router)
    app.include_router(mock_payment_router)

    return app


__all__ = ["create_api"]
