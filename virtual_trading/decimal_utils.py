"""
virtual_trading/decimal_utils.py

Purpose: Small Decimal-precision helpers shared by every calculation
module in this package (`portfolio_calculator.py`, `realized_pnl.py`,
`trading_stats.py`). Kept in their own module -- rather than living in
`portfolio_calculator.py` -- specifically to avoid a circular import:
`portfolio_calculator.py` imports `compute_realized_pnl` from
`realized_pnl.py`, so shared helpers can't live in
`portfolio_calculator.py` without `realized_pnl.py` importing back
from it.

Also kept separate from the project-root `utils.py`, which is scoped
to input *validation* ("everything here is oriented around
checking/validating data rather than transforming/formatting it", per
its own docstring) rather than numeric formatting -- and separate from
`helper.py`'s float-based currency formatting, since this module's
whole purpose is to stay in `Decimal` throughout rather than cast to
`float`.

Why Decimal here specifically: `virtual_accounts`/`virtual_holdings`/
`virtual_transactions` all use MySQL `DECIMAL(18,4)` columns, and
SQLAlchemy returns those as native `decimal.Decimal` values. The rest
of this project's Python layer casts straight to `float` on read
(see `database/portfolio_service.py`, `portfolio/realized_pnl.py`,
etc.) -- acceptable there, but the virtual trading calculation layer
is required to stay Decimal-safe end-to-end to avoid floating-point
rounding error in monetary figures.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

ZERO = Decimal("0")
_CENTS = Decimal("0.01")
_QUANTITY_PRECISION = Decimal("0.0001")


def to_decimal(value) -> Decimal:
    """
    Convert any numeric value (Decimal, float, int, str, None) to a
    Decimal safely. Converts via `str()` rather than passing a float
    directly to `Decimal()`, since `Decimal(0.1)` reproduces the
    binary floating-point value's imprecision while `Decimal(str(0.1))`
    does not.
    """
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return ZERO


def safe_divide_decimal(numerator: Decimal, denominator: Decimal, default: Decimal = ZERO) -> Decimal:
    """Decimal-safe division, returning `default` instead of raising on division by zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def quantize_money(value: Decimal) -> Decimal:
    """Round a Decimal to 2 places (currency), for display/reporting."""
    return to_decimal(value).quantize(_CENTS, rounding=ROUND_HALF_UP)


def quantize_quantity(value: Decimal) -> Decimal:
    """Round a Decimal to 4 places (share quantity), matching the DECIMAL(18,4) column precision."""
    return to_decimal(value).quantize(_QUANTITY_PRECISION, rounding=ROUND_HALF_UP)


def quantize_percent(value: Decimal) -> Decimal:
    """Round a Decimal to 2 places (percentage)."""
    return to_decimal(value).quantize(_CENTS, rounding=ROUND_HALF_UP)
