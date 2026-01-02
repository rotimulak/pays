"""Token API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas.tokens import (
    ErrorResponse,
    SpendTokensRequest,
    SpendTokensResponse,
    TokenBalanceResponse,
    TokenErrorCode,
)
from src.core.exceptions import (
    ConcurrentModificationError,
    InsufficientBalanceError,
    NotFoundError,
    SubscriptionExpiredError,
    UserBlockedError,
)
from src.db.session import get_session
from src.services.token_service import TokenService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["tokens"])


@router.get(
    "/users/{user_id}/balance",
    response_model=TokenBalanceResponse,
    responses={
        401: {"description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_balance(
    user_id: int,
    _api_key: str = Depends(verify_api_key),
) -> TokenBalanceResponse:
    """Get user's token balance and subscription status.

    Requires API key authentication.

    Args:
        user_id: Telegram user ID

    Returns:
        Current balance and subscription info
    """
    async with get_session() as session:
        service = TokenService(session)

        try:
            balance = await service.check_balance(user_id)
        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": TokenErrorCode.USER_NOT_FOUND,
                    "message": f"User {user_id} not found",
                },
            )

        return TokenBalanceResponse(
            user_id=balance.user_id,
            token_balance=balance.token_balance,
            subscription_active=balance.subscription_active,
            subscription_end=balance.subscription_end,
            can_spend=balance.can_spend,
            reason=balance.reason,
        )


@router.post(
    "/users/{user_id}/spend",
    response_model=SpendTokensResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Subscription expired or user blocked"},
        404: {"model": ErrorResponse, "description": "User not found"},
        409: {"model": ErrorResponse, "description": "Insufficient balance or concurrent modification"},
    },
)
async def spend_tokens(
    user_id: int,
    request: SpendTokensRequest,
    _api_key: str = Depends(verify_api_key),
) -> SpendTokensResponse:
    """Spend tokens from user's balance.

    Requires API key authentication.

    Error codes:
    - `insufficient_balance`: Not enough tokens
    - `subscription_expired`: No active subscription
    - `user_blocked`: User is blocked
    - `user_not_found`: User doesn't exist
    - `concurrent_modification`: Race condition, retry

    Args:
        user_id: Telegram user ID
        request: Spend request with amount and description

    Returns:
        Transaction result with new balance
    """
    async with get_session() as session:
        service = TokenService(session)

        try:
            result = await service.spend_tokens(
                user_id=user_id,
                amount=request.amount,
                description=request.description,
                idempotency_key=request.idempotency_key,
                metadata=request.metadata,
            )
            await session.commit()

        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": TokenErrorCode.USER_NOT_FOUND,
                    "message": f"User {user_id} not found",
                },
            )

        except UserBlockedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": TokenErrorCode.USER_BLOCKED,
                    "message": "User is blocked",
                },
            )

        except SubscriptionExpiredError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": TokenErrorCode.SUBSCRIPTION_EXPIRED,
                    "message": str(e),
                },
            )

        except InsufficientBalanceError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": TokenErrorCode.INSUFFICIENT_BALANCE,
                    "message": str(e),
                    "details": {
                        "required": e.required,
                        "available": e.available,
                    },
                },
            )

        except ConcurrentModificationError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": TokenErrorCode.CONCURRENT_MODIFICATION,
                    "message": str(e),
                },
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": TokenErrorCode.INVALID_AMOUNT,
                    "message": str(e),
                },
            )

        return SpendTokensResponse(
            transaction_id=result.transaction_id,
            tokens_spent=result.tokens_spent,
            balance_before=result.balance_before,
            balance_after=result.balance_after,
        )
