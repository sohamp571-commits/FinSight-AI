"""
utils.py

Validation and small standalone utility functions. Distinct from
helper.py in that everything here is oriented around checking/validating
data rather than transforming/formatting it.
"""

import re
from datetime import datetime

from constants import SUPPORTED_EXCHANGES
from custom_exceptions import ValidationError

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
# Minimum 8 chars, at least one letter and one digit.
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")
TICKER_REGEX = re.compile(r"^[A-Z0-9.&-]{1,15}$")


def is_valid_email(email: str) -> bool:
    """Return True if `email` looks like a syntactically valid email address."""
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))


def is_strong_password(password: str) -> bool:
    """Return True if `password` meets the minimum strength policy."""
    return bool(password) and bool(PASSWORD_REGEX.match(password))


def is_valid_ticker(ticker: str) -> bool:
    """Return True if `ticker` is a syntactically valid stock ticker symbol."""
    return bool(ticker) and bool(TICKER_REGEX.match(ticker.strip().upper()))


def is_supported_exchange(exchange: str) -> bool:
    """Return True if `exchange` is one of the exchanges FinSight AI supports."""
    return exchange.strip().upper() in SUPPORTED_EXCHANGES


def validate_required_fields(data: dict, required_fields: list[str]) -> None:
    """
    Ensure every field in `required_fields` is present and non-empty in `data`.

    Raises:
        ValidationError: listing all missing fields, if any are absent.
    """
    missing = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")


def validate_positive_number(value: float, field_name: str = "value") -> None:
    """Raise ValidationError if `value` is not a positive number."""
    if value is None or value <= 0:
        raise ValidationError(f"'{field_name}' must be a positive number.")


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """Raise ValidationError if the date range is invalid (start after end)."""
    if start_date and end_date and start_date > end_date:
        raise ValidationError("Start date cannot be later than end date.")


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp `value` to the inclusive range [minimum, maximum]."""
    return max(minimum, min(value, maximum))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide two numbers, returning `default` instead of raising on division by zero."""
    if denominator == 0:
        return default
    return numerator / denominator
