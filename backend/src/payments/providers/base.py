"""Base payment provider interface."""

from abc import ABC, abstractmethod

from src.db.models.invoice import Invoice
from src.payments.schemas import WebhookData


class PaymentProvider(ABC):
    """Abstract base class for payment providers.

    All payment providers (Mock, Robokassa, etc.) must implement this interface.
    """

    @abstractmethod
    def generate_payment_url(self, invoice: Invoice) -> str:
        """Generate redirect URL for payment initiation.

        Args:
            invoice: Invoice to pay

        Returns:
            URL to redirect user for payment
        """

    @abstractmethod
    def generate_init_signature(
        self,
        out_sum: str,
        inv_id: int,
        shp_params: dict[str, str],
    ) -> str:
        """Generate signature for payment URL.

        Args:
            out_sum: Payment amount as string
            inv_id: Invoice ID for payment system
            shp_params: Custom Shp_* parameters

        Returns:
            Signature string (MD5 hash for Robokassa)
        """

    @abstractmethod
    def verify_result_signature(self, data: WebhookData) -> bool:
        """Verify ResultURL callback signature.

        Args:
            data: Parsed webhook data

        Returns:
            True if signature is valid
        """

    @abstractmethod
    def parse_webhook(self, raw_data: dict[str, str]) -> WebhookData:
        """Parse incoming webhook to unified format.

        Args:
            raw_data: Raw form data from webhook

        Returns:
            Parsed WebhookData
        """

    @abstractmethod
    def format_success_response(self, inv_id: int) -> str:
        """Format response for successful webhook processing.

        Args:
            inv_id: Invoice ID that was processed

        Returns:
            Response string (e.g., 'OK12345' for Robokassa)
        """
