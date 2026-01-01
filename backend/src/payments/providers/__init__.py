"""Payment providers module."""

from src.payments.providers.base import PaymentProvider


def get_payment_provider() -> PaymentProvider:
    """Factory function to get configured payment provider.

    Returns provider based on PAYMENT_PROVIDER setting.
    """
    from src.core.config import settings
    from src.payments.providers.mock.provider import MockPaymentProvider

    if settings.payment_provider == "mock":
        return MockPaymentProvider()

    # Future: add robokassa provider
    # if settings.payment_provider == "robokassa":
    #     from src.payments.providers.robokassa.provider import RobokassaProvider
    #     return RobokassaProvider()

    raise ValueError(f"Unknown payment provider: {settings.payment_provider}")


__all__ = [
    "PaymentProvider",
    "get_payment_provider",
]
