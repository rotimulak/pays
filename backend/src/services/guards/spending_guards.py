"""Guards for validating token spending."""

from dataclasses import dataclass
from datetime import datetime

from src.core.exceptions import (
    InsufficientBalanceError,
    SubscriptionExpiredError,
    UserBlockedError,
)
from src.db.models.user import User


@dataclass
class SpendingContext:
    """Context for spending validation."""

    user: User
    amount: int
    description: str


class SpendingGuard:
    """Guard for validating token spending.

    Encapsulates all spending validation rules.
    """

    def __init__(self, context: SpendingContext) -> None:
        self.context = context
        self.user = context.user
        self.amount = context.amount

    def validate_all(self) -> None:
        """Run all validations. Raises on failure."""
        self.check_user_not_blocked()
        self.check_subscription_active()
        self.check_sufficient_balance()

    def check_user_not_blocked(self) -> None:
        """Check user is not blocked.

        Raises:
            UserBlockedError: If user is blocked
        """
        if self.user.is_blocked:
            raise UserBlockedError(f"User {self.user.id} is blocked")

    def check_subscription_active(self) -> None:
        """Check user has active subscription.

        Raises:
            SubscriptionExpiredError: If subscription is expired or missing
        """
        now = datetime.utcnow()

        if self.user.subscription_end is None:
            raise SubscriptionExpiredError(
                "No subscription. Please purchase a plan."
            )

        if self.user.subscription_end <= now:
            raise SubscriptionExpiredError(
                f"Subscription expired on {self.user.subscription_end.strftime('%d.%m.%Y')}"
            )

    def check_sufficient_balance(self) -> None:
        """Check user has enough tokens.

        Raises:
            InsufficientBalanceError: If balance is insufficient
        """
        if self.user.token_balance < self.amount:
            raise InsufficientBalanceError(
                required=self.amount,
                available=self.user.token_balance,
            )


def validate_spending(user: User, amount: int, description: str) -> None:
    """Convenience function for spending validation.

    Validates all spending conditions for the given user and amount.

    Args:
        user: User model instance
        amount: Amount to spend
        description: Description of spending

    Raises:
        UserBlockedError: If user is blocked
        SubscriptionExpiredError: If subscription is expired
        InsufficientBalanceError: If balance is insufficient
    """
    context = SpendingContext(user=user, amount=amount, description=description)
    guard = SpendingGuard(context)
    guard.validate_all()
