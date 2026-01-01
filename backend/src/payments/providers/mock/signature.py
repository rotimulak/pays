"""Robokassa-compatible MD5 signature utilities."""

import hashlib
from decimal import Decimal


def format_sum(amount: Decimal) -> str:
    """Format amount for signature calculation.

    Robokassa requires specific format: no trailing zeros after decimal point.
    Examples: 100.00 -> "100", 99.50 -> "99.5", 199.99 -> "199.99"
    """
    # Normalize to remove trailing zeros
    normalized = amount.normalize()

    # Check if it's a whole number
    if normalized == normalized.to_integral_value():
        return str(int(normalized))

    return str(normalized)


def build_shp_string(shp_params: dict[str, str]) -> str:
    """Build Shp_* parameters string for signature.

    Parameters must be sorted alphabetically by key.
    Format: Shp_key1=value1:Shp_key2=value2
    """
    if not shp_params:
        return ""

    # Sort by key and format
    sorted_params = sorted(shp_params.items())
    return ":".join(f"{k}={v}" for k, v in sorted_params)


def generate_init_signature(
    merchant_login: str,
    out_sum: Decimal,
    inv_id: int,
    password_1: str,
    shp_params: dict[str, str] | None = None,
) -> str:
    """Generate signature for payment URL (init).

    Formula: MD5(MerchantLogin:OutSum:InvId:Password_1[:Shp_*])

    Args:
        merchant_login: Merchant login
        out_sum: Payment amount
        inv_id: Invoice ID
        password_1: First password
        shp_params: Optional Shp_* parameters (sorted alphabetically)

    Returns:
        MD5 hash in lowercase
    """
    sum_str = format_sum(out_sum)

    parts = [merchant_login, sum_str, str(inv_id), password_1]

    if shp_params:
        shp_string = build_shp_string(shp_params)
        if shp_string:
            parts.append(shp_string)

    data = ":".join(parts)
    return hashlib.md5(data.encode()).hexdigest()


def generate_result_signature(
    out_sum: Decimal,
    inv_id: int,
    password_2: str,
    shp_params: dict[str, str] | None = None,
) -> str:
    """Generate signature for result verification (webhook).

    Formula: MD5(OutSum:InvId:Password_2[:Shp_*])

    Args:
        out_sum: Payment amount
        inv_id: Invoice ID
        password_2: Second password
        shp_params: Optional Shp_* parameters (sorted alphabetically)

    Returns:
        MD5 hash in lowercase
    """
    sum_str = format_sum(out_sum)

    parts = [sum_str, str(inv_id), password_2]

    if shp_params:
        shp_string = build_shp_string(shp_params)
        if shp_string:
            parts.append(shp_string)

    data = ":".join(parts)
    return hashlib.md5(data.encode()).hexdigest()


def verify_result_signature(
    out_sum: Decimal,
    inv_id: int,
    signature: str,
    password_2: str,
    shp_params: dict[str, str] | None = None,
) -> bool:
    """Verify webhook signature.

    Args:
        out_sum: Payment amount from webhook
        inv_id: Invoice ID from webhook
        signature: Signature from webhook
        password_2: Second password
        shp_params: Shp_* parameters from webhook

    Returns:
        True if signature is valid
    """
    expected = generate_result_signature(out_sum, inv_id, password_2, shp_params)
    return signature.lower() == expected.lower()
