"""Webhook handlers for payment callbacks."""

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import PlainTextResponse

from src.db.session import get_session
from src.payments.providers import get_payment_provider
from src.payments.schemas import WebhookData
from src.services.audit_service import AuditService
from src.services.billing_service import BillingService
from src.services.notification_service import NotificationService
from src.bot import get_bot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/robokassa", response_class=PlainTextResponse)
async def robokassa_result_url(
    OutSum: Decimal = Form(...),
    InvId: int = Form(...),
    SignatureValue: str = Form(...),
    Shp_invoice_id: UUID = Form(...),
    Shp_user_id: int = Form(...),
    Fee: Decimal | None = Form(default=None),
    Email: str | None = Form(default=None),
    PaymentMethod: str | None = Form(default=None),
) -> PlainTextResponse:
    """ResultURL callback handler.

    Robokassa sends POST request here after successful payment.

    1. Verify signature
    2. Process payment via BillingService
    3. Return 'OK{InvId}'
    """
    logger.info(
        "Webhook received: inv_id=%d, sum=%s, invoice_id=%s, user_id=%d",
        InvId,
        OutSum,
        Shp_invoice_id,
        Shp_user_id,
    )

    # Parse webhook data
    webhook_data = WebhookData(
        out_sum=OutSum,
        inv_id=InvId,
        signature=SignatureValue,
        shp_invoice_id=Shp_invoice_id,
        shp_user_id=Shp_user_id,
        fee=Fee,
        email=Email,
        payment_method=PaymentMethod,
    )

    # Get payment provider and verify signature
    provider = get_payment_provider()

    if not provider.verify_result_signature(webhook_data):
        logger.warning("Invalid signature for inv_id=%d", InvId)
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process payment with billing service
    async with get_session() as session:
        billing_service = BillingService(session)

        # Set up audit service
        audit_service = AuditService(session)
        billing_service.set_audit_service(audit_service)

        # Set up notification service
        try:
            bot = get_bot()
            notification_service = NotificationService(bot)
            billing_service.set_notification_service(notification_service)
        except Exception as e:
            logger.warning("Could not initialize notification service: %s", e)

        try:
            invoice = await billing_service.process_successful_payment(
                invoice_id=webhook_data.shp_invoice_id
            )
            logger.info(
                "Payment processed: inv_id=%d, invoice_id=%s, status=%s",
                InvId,
                invoice.id,
                invoice.status.value,
            )
        except Exception as e:
            logger.error("Payment processing failed: %s", e)
            raise HTTPException(status_code=500, detail="Payment processing failed")

    # Return success response
    response = provider.format_success_response(InvId)
    return PlainTextResponse(content=response)
