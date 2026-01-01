"""Audit service for logging system events."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        user_id: int | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create audit log entry.

        Args:
            action: Action name (e.g., "payment.processed", "user.created")
            entity_type: Type of entity (e.g., "invoice", "user")
            entity_id: ID of affected entity
            user_id: Telegram user ID if applicable
            old_value: State before change (as dict)
            new_value: State after change (as dict)
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            metadata_=metadata or {},
        )

        self.session.add(audit_log)
        await self.session.flush()

        logger.debug(
            "Audit log created: action=%s, entity_type=%s, entity_id=%s",
            action,
            entity_type,
            entity_id,
        )

        return audit_log

    async def log_payment_processed(
        self,
        user_id: int,
        invoice_id: UUID,
        old_balance: int,
        new_balance: int,
        old_subscription: datetime | None,
        new_subscription: datetime | None,
    ) -> AuditLog:
        """Log successful payment processing."""
        return await self.log_action(
            action="payment.processed",
            entity_type="invoice",
            entity_id=str(invoice_id),
            user_id=user_id,
            old_value={
                "token_balance": old_balance,
                "subscription_end": old_subscription.isoformat() if old_subscription else None,
            },
            new_value={
                "token_balance": new_balance,
                "subscription_end": new_subscription.isoformat() if new_subscription else None,
            },
        )

    async def log_user_created(self, user_id: int, username: str | None) -> AuditLog:
        """Log new user registration."""
        return await self.log_action(
            action="user.created",
            entity_type="user",
            entity_id=str(user_id),
            user_id=user_id,
            new_value={"username": username},
        )

    async def log_invoice_created(
        self,
        user_id: int,
        invoice_id: UUID,
        tariff_slug: str,
        amount: float,
    ) -> AuditLog:
        """Log invoice creation."""
        return await self.log_action(
            action="invoice.created",
            entity_type="invoice",
            entity_id=str(invoice_id),
            user_id=user_id,
            new_value={
                "tariff_slug": tariff_slug,
                "amount": amount,
            },
        )

    async def log_tokens_spent(
        self,
        user_id: int,
        amount: int,
        old_balance: int,
        new_balance: int,
        reason: str,
    ) -> AuditLog:
        """Log token spending."""
        return await self.log_action(
            action="tokens.spent",
            entity_type="user",
            entity_id=str(user_id),
            user_id=user_id,
            old_value={"token_balance": old_balance},
            new_value={"token_balance": new_balance},
            metadata={"amount": amount, "reason": reason},
        )

    async def log_invoices_expired(
        self,
        count: int,
        cutoff_time: datetime,
        ttl_hours: int,
    ) -> AuditLog:
        """Log batch invoice expiration."""
        return await self.log_action(
            action="invoices.expired",
            entity_type="system",
            metadata={
                "count": count,
                "cutoff_time": cutoff_time.isoformat(),
                "ttl_hours": ttl_hours,
            },
        )
