from typing import Any


class AppException(Exception):
    """Base application exception."""

    error_code: str = "APP_ERROR"
    message: str = "An application error occurred"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(error_code={self.error_code!r}, message={self.message!r})"


class NotFoundError(AppException):
    """Resource not found."""

    error_code = "NOT_FOUND"
    message = "Resource not found"


class ValidationError(AppException):
    """Validation error."""

    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class PaymentError(AppException):
    """Payment processing error."""

    error_code = "PAYMENT_ERROR"
    message = "Payment processing failed"


class InsufficientBalanceError(AppException):
    """Not enough tokens in balance."""

    error_code = "INSUFFICIENT_BALANCE"
    message = "Insufficient token balance"

    def __init__(
        self,
        required: int,
        available: int,
        message: str | None = None,
    ) -> None:
        self.required = required
        self.available = available
        super().__init__(
            message=message or f"Insufficient balance: need {required}, have {available}",
            details={"required": required, "available": available},
        )


class SubscriptionExpiredError(AppException):
    """Subscription is expired or not active."""

    error_code = "SUBSCRIPTION_EXPIRED"
    message = "Subscription expired"


class UserBlockedError(AppException):
    """User is blocked from operations."""

    error_code = "USER_BLOCKED"
    message = "User is blocked"


class ConcurrentModificationError(AppException):
    """Race condition detected during modification."""

    error_code = "CONCURRENT_MODIFICATION"
    message = "Resource was modified by another operation. Please retry."


class DuplicateError(AppException):
    """Duplicate operation (idempotency violation)."""

    error_code = "DUPLICATE"
    message = "Operation already performed"


class OptimisticLockError(AppException):
    """Optimistic lock conflict."""

    error_code = "OPTIMISTIC_LOCK"
    message = "Resource was modified by another operation"
