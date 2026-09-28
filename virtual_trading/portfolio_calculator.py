"""
virtual_trading/portfolio_calculator.py

Purpose: Pure calculation layer combining a user's virtual account
(cash), virtual holdings (cost basis), live/overridden market prices,
and Realized P&L (`realized_pnl.py`, this package) into the headline
numbers the Virtual Trading dashboard displays. Mirrors the shape and
responsibilities of `portfolio/portfolio_calculator.py` (the real
-money equivalent) with two differences:
    - works entirely in `Decimal`, not `float`, per Batch 13's
      requirement that virtual trading calculations avoid
      floating-point rounding error for monetary figures;
    - combines Realized + Unrealized P&L into one Total P&L / Return %
      figure here, since (unlike the real portfolio, which already has
      a separate Analytics tab showing Realized P&L on its own) there
      is no existing place doing that combination for virtual trading
      yet.

For live current prices, reuses the project's single existing market
-data gateway, `dashboard.market_data_service.fetch_quotes_bulk` --
the exact same function `portfolio/portfolio_service.py` uses for the
real portfolio's live valuation -- rather than adding a second
integration with yfinance or any other data source. That function
already returns `{ticker: str, price: float, previous_close: float,
change: float, change_pct: float, volume, day_high, day_low}` per
ticker, or omits a ticker entirely if it could not be fetched; the
float values it returns are converted to Decimal via `to_decimal()`
before any arithmetic happens.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from database.models import VirtualHolding
from database.virtual_account_service import virtual_account_service
from database.virtual_holding_service import virtual_holding_service
from logging_config import logger
from virtual_trading.decimal_utils import ZERO, quantize_money, quantize_percent, quantize_quantity, safe_divide_decimal, to_decimal
from virtual_trading.realized_pnl import compute_realized_pnl


@dataclass
class VirtualHoldingSnapshot:
    """Per-holding valuation at a single point in time."""

    ticker_symbol: str
    quantity: Decimal
    average_buy_price: Decimal
    current_price: Decimal
    invested_value: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    price_is_live: bool  # False when no live/override quote was available and cost basis was used instead


@dataclass
class VirtualPortfolioOverview:
    """The full headline overview for a user's virtual trading account."""

    cash_balance: Decimal
    initial_capital: Decimal
    total_invested: Decimal
    current_holdings_value: Decimal
    total_portfolio_value: Decimal  # cash_balance + current_holdings_value
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    realized_pnl: Decimal
    todays_pnl: Decimal
    todays_pnl_pct: Decimal
    total_pnl: Decimal  # realized_pnl + unrealized_pnl
    return_pct: Decimal  # total_pnl / initial_capital * 100
    holdings_count: int
    holdings: list[VirtualHoldingSnapshot] = field(default_factory=list)


def _fetch_live_quotes(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """
    Fetch live quotes for the given tickers via the project's existing
    market-data gateway. Never raises -- `fetch_quotes_bulk` already
    degrades gracefully to an empty/partial result if the data
    provider is unreachable, and callers here already handle a ticker
    being absent from the result (fall back to cost basis), exactly
    like `portfolio/portfolio_service.py` does for the real portfolio.
    """
    if not tickers:
        return {}
    try:
        from dashboard.market_data_service import fetch_quotes_bulk

        return fetch_quotes_bulk(tuple(sorted(set(tickers))))
    except Exception as exc:  # noqa: BLE001 - live market data is best-effort; never break the calculator
        logger.warning(f"Live market data unavailable for virtual portfolio valuation: {exc}")
        return {}


def compute_portfolio_overview(
    user_id: int, current_prices: dict[str, Decimal | float | str] | None = None
) -> VirtualPortfolioOverview:
    """
    Compute the full Decimal-precision overview for a user's virtual
    trading account: cash balance, invested value, current portfolio
    value, unrealized/realized/today's/total P&L, and return %.

    Args:
        user_id: whose virtual account/holdings to value.
        current_prices: optional {ticker: price} override. When
            omitted (the normal/production path), live prices are
            fetched via the project's existing market-data service.
            When supplied -- e.g. by a caller that already has fresher
            quotes, or by a test that must not depend on network
            access -- those prices are used instead and no live fetch
            occurs; in that case `todays_pnl` is reported as 0, since
            no `previous_close` is available without a live quote.
            A ticker with no price available (missing from both the
            override and the live-quote result) never has a price
            invented for it -- it falls back to that holding's own
            average buy price, exactly like the real portfolio's
            `portfolio_summary()`, which also makes its unrealized P&L
            correctly show 0 for that position rather than a fabricated
            gain/loss.

    Handles: no holdings, zero invested value (return % is 0, not a
    ZeroDivisionError), and a missing/invalid market price for any
    individual ticker.
    """
    account = virtual_account_service.get_or_create(user_id)
    cash_balance = to_decimal(account.cash_balance)
    initial_capital = to_decimal(account.initial_capital)

    holdings: list[VirtualHolding] = virtual_holding_service.get_user_holdings(user_id, page_size=1000)["items"]
    tickers = [h.ticker_symbol for h in holdings]

    quotes: dict[str, dict[str, Any]] = {}
    price_overrides: dict[str, Decimal] | None = None
    if current_prices is not None:
        price_overrides = {ticker.strip().upper(): to_decimal(price) for ticker, price in current_prices.items()}
    else:
        quotes = _fetch_live_quotes(tickers)

    holding_snapshots: list[VirtualHoldingSnapshot] = []
    total_invested = ZERO
    total_current_value = ZERO
    todays_pnl = ZERO
    todays_previous_value = ZERO

    for holding in holdings:
        quantity = to_decimal(holding.quantity)
        avg_price = to_decimal(holding.average_buy_price)
        invested = quantity * avg_price

        if price_overrides is not None:
            market_price = price_overrides.get(holding.ticker_symbol, avg_price)
            price_is_live = holding.ticker_symbol in price_overrides
        else:
            quote = quotes.get(holding.ticker_symbol)
            if quote is not None:
                market_price = to_decimal(quote["price"])
                price_is_live = True
                previous_close = to_decimal(quote["previous_close"])
                todays_pnl += quantity * (market_price - previous_close)
                todays_previous_value += quantity * previous_close
            else:
                market_price = avg_price
                price_is_live = False

        current_value = quantity * market_price
        unrealized = current_value - invested
        unrealized_pct = safe_divide_decimal(unrealized, invested) * 100 if invested else ZERO

        holding_snapshots.append(
            VirtualHoldingSnapshot(
                ticker_symbol=holding.ticker_symbol,
                quantity=quantize_quantity(quantity),
                average_buy_price=quantize_money(avg_price),
                current_price=quantize_money(market_price),
                invested_value=quantize_money(invested),
                current_value=quantize_money(current_value),
                unrealized_pnl=quantize_money(unrealized),
                unrealized_pnl_pct=quantize_percent(unrealized_pct),
                price_is_live=price_is_live,
            )
        )
        total_invested += invested
        total_current_value += current_value

    realized_report = compute_realized_pnl(user_id)
    realized_pnl = realized_report.total_realized_pnl

    unrealized_pnl_total = total_current_value - total_invested
    unrealized_pnl_pct_total = (
        safe_divide_decimal(unrealized_pnl_total, total_invested) * 100 if total_invested else ZERO
    )
    todays_pnl_pct = safe_divide_decimal(todays_pnl, todays_previous_value) * 100 if todays_previous_value else ZERO

    total_pnl = realized_pnl + unrealized_pnl_total
    return_pct = safe_divide_decimal(total_pnl, initial_capital) * 100 if initial_capital else ZERO

    total_portfolio_value = cash_balance + total_current_value

    return VirtualPortfolioOverview(
        cash_balance=quantize_money(cash_balance),
        initial_capital=quantize_money(initial_capital),
        total_invested=quantize_money(total_invested),
        current_holdings_value=quantize_money(total_current_value),
        total_portfolio_value=quantize_money(total_portfolio_value),
        unrealized_pnl=quantize_money(unrealized_pnl_total),
        unrealized_pnl_pct=quantize_percent(unrealized_pnl_pct_total),
        realized_pnl=quantize_money(realized_pnl),
        todays_pnl=quantize_money(todays_pnl),
        todays_pnl_pct=quantize_percent(todays_pnl_pct),
        total_pnl=quantize_money(total_pnl),
        return_pct=quantize_percent(return_pct),
        holdings_count=len(holding_snapshots),
        holdings=holding_snapshots,
    )
