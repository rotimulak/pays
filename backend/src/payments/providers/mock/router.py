"""Mock payment router for FastAPI."""

import logging
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.config import settings
from src.payments.providers.mock.signature import generate_result_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock-payment", tags=["mock-payment"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def payment_page(
    request: Request,
    MerchantLogin: str,
    OutSum: str,
    InvId: int,
    Description: str,
    SignatureValue: str,
    Shp_invoice_id: UUID,
    Shp_user_id: int,
    Culture: str = "ru",
    IsTest: str | None = None,
) -> HTMLResponse:
    """Display mock payment page.

    Parses query parameters in Robokassa format.
    """
    return templates.TemplateResponse(
        "payment_page.html",
        {
            "request": request,
            "merchant_login": MerchantLogin,
            "out_sum": OutSum,
            "inv_id": InvId,
            "description": Description,
            "shp_invoice_id": str(Shp_invoice_id),
            "shp_user_id": Shp_user_id,
        },
    )


@router.post("/process", response_class=HTMLResponse)
async def process_payment(
    request: Request,
    OutSum: str = Form(...),
    InvId: int = Form(...),
    Shp_invoice_id: str = Form(...),
    Shp_user_id: int = Form(...),
) -> HTMLResponse:
    """Process mock payment (simulate successful payment).

    1. Generate result signature
    2. Send POST to webhook endpoint
    3. Show success page
    """
    out_sum = Decimal(OutSum)

    # Build Shp_* params for signature
    shp_params = {
        "Shp_invoice_id": Shp_invoice_id,
        "Shp_user_id": str(Shp_user_id),
    }

    # Generate signature for webhook
    signature = generate_result_signature(
        out_sum=out_sum,
        inv_id=InvId,
        password_2=settings.mock_password_2,
        shp_params=shp_params,
    )

    # Prepare webhook data
    webhook_data = {
        "OutSum": OutSum,
        "InvId": str(InvId),
        "SignatureValue": signature,
        "Shp_invoice_id": Shp_invoice_id,
        "Shp_user_id": str(Shp_user_id),
    }

    # Send POST to webhook endpoint
    webhook_url = f"{settings.webhook_base_url.rstrip('/')}/webhook/robokassa"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                data=webhook_data,
                timeout=10.0,
            )
            logger.info(
                "Webhook response: status=%d, body=%s",
                response.status_code,
                response.text,
            )
    except Exception as e:
        logger.error("Webhook request failed: %s", e)

    # Show success page
    return templates.TemplateResponse(
        "success.html",
        {
            "request": request,
            "out_sum": OutSum,
            "inv_id": InvId,
        },
    )


@router.post("/cancel", response_class=HTMLResponse)
async def cancel_payment(
    request: Request,
    InvId: int = Form(...),
    Shp_invoice_id: str = Form(...),
) -> HTMLResponse:
    """Cancel mock payment.

    Shows cancellation page. Does not call webhook.
    """
    logger.info("Payment cancelled: inv_id=%d", InvId)

    return templates.TemplateResponse(
        "fail.html",
        {
            "request": request,
            "inv_id": InvId,
        },
    )
