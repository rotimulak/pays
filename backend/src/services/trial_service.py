"""Trial tariff activation service."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ValidationError
from src.db.models.promo_activation import PromoActivation
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.promo_activation_repository import PromoActivationRepository
from src.db.repositories.promo_code_repository import PromoCodeRepository
from src.db.repositories.tariff_repository import TariffRepository
from src.db.repositories.transaction_repository import TransactionRepository
from src.db.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class TrialService:
    """Service for trial tariff activation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.tariff_repo = TariffRepository(session)
        self.promo_repo = PromoCodeRepository(session)
        self.activation_repo = PromoActivationRepository(session)
        self.transaction_repo = TransactionRepository(session)

    async def activate_trial(self, user_id: int, promo_code: str) -> dict:
        """Activate trial tariff for user.

        Args:
            user_id: User's Telegram ID
            promo_code: Promo code string

        Returns:
            Dict with activation details:
            - tokens_credited: int
            - subscription_end: datetime
            - tariff_name: str
            - new_balance: int

        Raises:
            ValidationError: If activation is not possible
        """
        # 1. Validate promo code
        promo = await self.promo_repo.get_by_code(promo_code)
        if not promo:
            raise ValidationError(message="Промокод не найден")

        if not promo.tariff_id:
            raise ValidationError(message="Промокод не привязан к тарифу")

        # 2. Get tariff
        tariff = await self.tariff_repo.get_by_id(promo.tariff_id)
        if not tariff:
            raise ValidationError(message="Тариф не найден")

        # 3. Check if user already activated this tariff
        already_activated = await self.activation_repo.has_activated_tariff(
            user_id, tariff.id
        )
        if already_activated:
            raise ValidationError(
                message=f"Вы уже активировали тариф '{tariff.name}' ранее"
            )

        # 4. Validate promo code availability
        is_valid, error = await self.promo_repo.is_valid(promo, tariff.id)
        if not is_valid:
            raise ValidationError(message=error or "Промокод недействителен")

        # 5. Get user
        user = await self.user_repo.get_for_update(user_id)
        if not user:
            raise ValidationError(message="Пользователь не найден")

        # 6. Credit tokens
        tokens_to_credit = tariff.tokens
        if tokens_to_credit > 0:
            user = await self.user_repo.update_balance(
                user_id=user_id,
                delta=tokens_to_credit,
                expected_version=user.balance_version,
            )

        # 7. Extend subscription (calculate based on period_value)
        # User requirement: +8 days (period_value from tariff)
        days_to_add = tariff.period_value
        now = datetime.utcnow()

        if user.subscription_end and user.subscription_end > now:
            # Add to existing subscription
            new_subscription_end = user.subscription_end + timedelta(days=days_to_add)
        else:
            # Start from now
            new_subscription_end = now + timedelta(days=days_to_add)

        await self.user_repo.update_subscription(user_id, new_subscription_end)

        # 8. Create activation record
        activation = PromoActivation(
            user_id=user_id,
            tariff_id=tariff.id,
            promo_code_id=promo.id,
            tokens_credited=tokens_to_credit,
            subscription_days_added=days_to_add,
        )
        await self.activation_repo.create(activation)

        # 9. Increment promo uses
        await self.promo_repo.increment_uses(promo.id)

        # 10. Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.TOPUP,
            tokens_delta=tokens_to_credit,
            balance_after=user.token_balance,
            description=f"Промо-тариф активирован: +{tokens_to_credit} токенов, подписка до {new_subscription_end.strftime('%d.%m.%Y')}",
            metadata_={
                "promo_code": promo_code,
                "tariff_slug": tariff.slug,
                "subscription_days_added": days_to_add,
            },
        )
        await self.transaction_repo.create(transaction)

        await self.session.commit()

        logger.info(
            "Trial activated: user=%d, tariff=%s, tokens=%d, days=%d",
            user_id,
            tariff.slug,
            tokens_to_credit,
            days_to_add,
        )

        return {
            "tokens_credited": tokens_to_credit,
            "subscription_end": new_subscription_end,
            "tariff_name": tariff.name,
            "new_balance": user.token_balance,
        }
