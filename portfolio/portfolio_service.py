"""
portfolio/portfolio_service.py

Purpose: The application-level entry point for portfolio holdings.
Deliberately does NOT reimplement CRUD or cost-basis math -- both
already exist in `database.portfolio_service` (Phase 3, the `portfolio`
table). This module only adds what Phase 3 couldn't: operations that
need *live* market data (today's gain/loss, top winner/loser), which
belong in the `portfolio/` application layer rather than the
Streamlit-free `database/` service layer (which has no concept of
"live quotes").
"""

from typing import Any

from custom_exceptions import FinSightBaseException
from dashboard.market_data_service import fetch_quotes_bulk
from database.models import Portfolio
from database.portfolio_service import portfolio_service as _db_portfolio_service
from logging_config import logger

# Re-exported so callers in portfolio/ only ever need one import path for
# holding CRUD, exactly like stock_search.search_service re-exports
# watchlist_service for favorites.
get_user_holdings = _db_portfolio_service.get_user_holdings
add_stock = _db_portfolio_service.add_stock
remove_stock = _db_portfolio_service.remove_stock
update_holding = _db_portfolio_service.update_holding
current_investment = _db_portfolio_service.current_investment


def get_live_quotes_for_holdings(holdings: list[Portfolio]) -> dict[str, dict[str, Any]]:
    """Fetch live quotes (price, previous_close, change_pct, ...) for every held ticker in one batch call."""
    if not holdings:
        return {}
    tickers = tuple(sorted({h.ticker_symbol for h in holdings}))
    return fetch_quotes_bulk(tickers)


def get_portfolio_summary_live(user_id: int) -> dict[str, Any]:
    """
    Build a portfolio summary valued at *live* market prices, reusing
    Phase 3's `portfolio_summary()` (which already accepts an optional
    `current_prices` override) rather than recomputing valuation math.
    """
    holdings = get_user_holdings(user_id, page_size=1000)["items"]
    quotes = get_live_quotes_for_holdings(holdings)
    current_prices = {ticker: quote["price"] for ticker, quote in quotes.items()}

    try:
        return _db_portfolio_service.portfolio_summary(user_id, current_prices=current_prices)
    except FinSightBaseException as exc:
        logger.error(f"Failed to build live portfolio summary for user_id={user_id}: {exc}")
        raise


def get_todays_gain_loss(user_id: int) -> dict[str, float]:
    """
    Compute today's (intraday) portfolio gain/loss -- distinct from
    total profit/loss, which is relative to average buy price. Uses
    each holding's live `previous_close` vs current price, which Phase
    3's cost-basis-only `portfolio_summary()` has no way to express.
    """
    holdings = get_user_holdings(user_id, page_size=1000)["items"]
    quotes = get_live_quotes_for_holdings(holdings)

    todays_gain_loss = 0.0
    todays_gain_loss_pct_weighted = 0.0
    total_previous_value = 0.0

    for holding in holdings:
        quote = quotes.get(holding.ticker_symbol)
        if quote is None:
            continue
        quantity = float(holding.quantity)
        previous_value = quantity * quote["previous_close"]
        current_value = quantity * quote["price"]
        todays_gain_loss += current_value - previous_value
        total_previous_value += previous_value

    todays_gain_loss_pct = (todays_gain_loss / total_previous_value * 100) if total_previous_value else 0.0

    return {
        "todays_gain_loss": round(todays_gain_loss, 2),
        "todays_gain_loss_pct": round(todays_gain_loss_pct, 2),
    }


def get_top_winner_and_loser(user_id: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Identify the best- and worst-performing holdings by total profit/loss percentage."""
    summary = get_portfolio_summary_live(user_id)
    holdings = summary["holdings"]
    if not holdings:
        return None, None

    top_winner = max(holdings, key=lambda h: h["profit_loss_pct"])
    top_loser = min(holdings, key=lambda h: h["profit_loss_pct"])
    return top_winner, top_loser
