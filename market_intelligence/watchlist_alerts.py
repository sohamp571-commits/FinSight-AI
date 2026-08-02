"""
market_intelligence/watchlist_alerts.py

Purpose: Monitors every ticker on a user's *watchlist* (Phase 3
`database.watchlist_service`, reused with no schema changes) for
significant daily price moves -- distinct from price_alerts.py, which
only fires for alerts the user explicitly configured a target for.
This covers the "Watchlist Price Alerts" subscription category for
users who simply want to be told when something on their watchlist
moves a lot, without setting up a specific price target.
"""

from database.database import db_manager
from database.models import Watchlist
from database.watchlist_service import watchlist_service
from dashboard.market_data_service import fetch_quote
from logging_config import logger
from market_intelligence.notification_service import create_notification, should_notify

SIGNIFICANT_MOVE_THRESHOLD_PCT = 5.0


def _get_all_watchlisted_user_ticker_pairs() -> list[tuple[int, str]]:
    """Return every (user_id, ticker_symbol) pair currently on any watchlist."""
    all_entries = db_manager.get_all(Watchlist, limit=5000)
    return [(entry.user_id, entry.ticker_symbol) for entry in all_entries]


def check_watchlist_price_moves() -> int:
    """
    Check every watchlisted ticker for a same-day move beyond
    SIGNIFICANT_MOVE_THRESHOLD_PCT and notify subscribed users.
    Intended to be invoked periodically by notification_scheduler.py.

    Returns:
        The number of notifications created during this run.
    """
    pairs = _get_all_watchlisted_user_ticker_pairs()
    if not pairs:
        return 0

    unique_tickers = {ticker for _, ticker in pairs}
    quotes = {ticker: fetch_quote(ticker) for ticker in unique_tickers}

    notified_count = 0
    for user_id, ticker in pairs:
        quote = quotes.get(ticker)
        if quote is None or abs(quote["change_pct"]) < SIGNIFICANT_MOVE_THRESHOLD_PCT:
            continue
        if not should_notify(user_id, "watchlist_price_alerts"):
            continue

        direction = "surged" if quote["change_pct"] > 0 else "dropped"
        create_notification(
            user_id=user_id,
            notification_type="WATCHLIST_PRICE_MOVE",
            title=f"{ticker} {direction} {abs(quote['change_pct']):.2f}%",
            message=(
                f"{ticker} on your watchlist has {direction} {abs(quote['change_pct']):.2f}% today "
                f"to {quote['price']:,.2f}."
            ),
            priority="MEDIUM",
            related_ticker=ticker,
        )
        notified_count += 1

    if notified_count:
        logger.info(f"Watchlist price move check complete: {notified_count} notification(s) created.")
    return notified_count


def get_watchlist_movers_for_user(user_id: int) -> list[dict]:
    """Return today's price moves for one user's watchlist, for a dashboard summary widget."""
    entries = watchlist_service.list_watchlist(user_id, page_size=100)["items"]
    movers = []
    for entry in entries:
        quote = fetch_quote(entry.ticker_symbol)
        if quote:
            movers.append({"ticker": entry.ticker_symbol, "price": quote["price"], "change_pct": quote["change_pct"]})
    return sorted(movers, key=lambda m: abs(m["change_pct"]), reverse=True)
