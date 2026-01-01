"""Mock payment provider implementation."""

from decimal import Decimal
from urllib.parse import urlencode
from uuid import UUID

from src.core.config import settings
from src.db.models.invoice import Invoice
from src.payments.providers.base import PaymentProvider
from src.payments.providers.mock.signature import (
    generate_init_signature,
    generate_result_signature,
    verify_result_signature as verify_sig,
)
from src.payments.schemas import WebhookData


class MockPaymentProvider(PaymentProvider):
    """Mock payment provider for testing.

    Implements the same interface and signature algorithms as Robokassa,
    but uses local endpoints for payment simulation.
    """

    def __init__(self) -> None:
        self.merchant_login = settings.mock_merchant_login
        self.password_1 = settings.mock_password_1
        self.password_2 = settings.mock_password_2
        self.base_url = settings.webhook_base_url.rstrip("/")

    def generate_payment_url(self, invoice: Invoice) -> str:
        """Generate mock payment page URL.

        Creates URL with same parameters as Robokassa.
        """
        shp_params = self._build_shp_params(invoice)

        signature = generate_init_signature(
            merchant_login=self.merchant_login,
            out_sum=invoice.amount,
            inv_id=invoice.inv_id,
            password_1=self.password_1,
            shp_params=shp_params,
        )

        # Build description
        description = f"Оплата тарифа #{invoice.inv_id}"

        # Build query parameters (Robokassa format)
        params = {
            "MerchantLogin": self.merchant_login,
            "OutSum": str(invoice.amount),
            "InvId": invoice.inv_id,
            "Description": description,
            "SignatureValue": signature,
            "Culture": "ru",
        }

        # Add Shp_* parameters
        for key, value in shp_params.items():
            params[key] = value

        # Add test flag if configured
        if settings.robokassa_is_test:
            params["IsTest"] = "1"

        return f"{self.base_url}/mock-payment?{urlencode(params)}"

    def generate_init_signature(
        self,
        out_sum: str,
        inv_id: int,
        shp_params: dict[str, str],
    ) -> str:
        """Generate signature for payment URL."""
        return generate_init_signature(
            merchant_login=self.merchant_login,
            out_sum=Decimal(out_sum),
            inv_id=inv_id,
            password_1=self.password_1,
            shp_params=shp_params,
        )

    def verify_result_signature(self, data: WebhookData) -> bool:
        """Verify webhook signature."""
        shp_params = {
            "Shp_invoice_id": str(data.shp_invoice_id),
            "Shp_user_id": str(data.shp_user_id),
        }

        return verify_sig(
            out_sum=data.out_sum,
            inv_id=data.inv_id,
            signature=data.signature,
            password_2=self.password_2,
            shp_params=shp_params,
        )

    def parse_webhook(self, raw_data: dict[str, str]) -> WebhookData:
        """Parse webhook form data to WebhookData."""
        return WebhookData(
            out_sum=Decimal(raw_data["OutSum"]),
            inv_id=int(raw_data["InvId"]),
            signature=raw_data["SignatureValue"],
            shp_invoice_id=UUID(raw_data["Shp_invoice_id"]),
            shp_user_id=int(raw_data["Shp_user_id"]),
            fee=Decimal(raw_data["Fee"]) if "Fee" in raw_data else None,
            email=raw_data.get("Email"),
            payment_method=raw_data.get("PaymentMethod"),
        )

    def format_success_response(self, inv_id: int) -> str:
        """Format success response for webhook."""
        return f"OK{inv_id}"

    def generate_webhook_signature(
        self,
        out_sum: Decimal,
        inv_id: int,
        shp_params: dict[str, str],
    ) -> str:
        """Generate signature for webhook (result URL).

        Used by mock payment page to simulate Robokassa callback.
        """
        return generate_result_signature(
            out_sum=out_sum,
            inv_id=inv_id,
            password_2=self.password_2,
            shp_params=shp_params,
        )

    @staticmethod
    def _build_shp_params(invoice: Invoice) -> dict[str, str]:
        """Build Shp_* parameters for invoice."""
        return {
            "Shp_invoice_id": str(invoice.id),
            "Shp_user_id": str(invoice.user_id),
        }
