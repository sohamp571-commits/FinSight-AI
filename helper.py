"""
helper.py

General-purpose helper functions used across multiple modules
(formatting, hashing, string handling). Business-logic-specific
helpers belong in their own module's package instead.
"""

import re
import secrets
import string
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import bcrypt

from constants import DATE_FORMAT, DATETIME_FORMAT, DISPLAY_DATE_FORMAT
from custom_exceptions import ValidationError
from logging_config import logger


# ==========================================================
# Password Hashing
# ==========================================================
def hash_password(plain_password: str, rounds: int = 12) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        plain_password: The raw password supplied by the user.
        rounds: bcrypt work factor (cost).

    Returns:
        The bcrypt hash as a UTF-8 string, safe to store in the database.
    """
    if not plain_password:
        raise ValidationError("Password must not be empty.")
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        logger.error(f"Password verification failed: {exc}")
        return False


# ==========================================================
# Token / Random Generation
# ==========================================================
def generate_secure_token(length: int = 32) -> str:
    """Generate a URL-safe random token (e.g. for password resets, session IDs)."""
    return secrets.token_urlsafe(length)


def generate_random_string(length: int = 12) -> str:
    """Generate a random alphanumeric string, e.g. for temporary identifiers."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ==========================================================
# Formatting Helpers
# ==========================================================
def format_currency(amount: float | Decimal, currency_symbol: str = "₹") -> str:
    """Format a numeric amount as a currency string with 2 decimal places."""
    quantized = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{currency_symbol}{quantized:,}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a float as a percentage string, e.g. 3.4567 -> '3.46%'."""
    return f"{value:.{decimals}f}%"


def format_date(value: datetime, display: bool = True) -> str:
    """Format a datetime object using the project's standard date formats."""
    if value is None:
        return ""
    return value.strftime(DISPLAY_DATE_FORMAT if display else DATE_FORMAT)


def format_datetime(value: datetime) -> str:
    """Format a datetime object using the project's standard datetime format."""
    if value is None:
        return ""
    return value.strftime(DATETIME_FORMAT)


# ==========================================================
# String Helpers
# ==========================================================
def slugify(value: str) -> str:
    """Convert a string into a lowercase, hyphen-separated slug."""
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[\s_]+", "-", value)


def truncate_text(value: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length, appending a suffix if truncated."""
    if len(value) <= max_length:
        return value
    return value[: max_length - len(suffix)].rstrip() + suffix
