"""
market_intelligence/news_alerts.py

Purpose: Checks for breaking news (via news_classifier.py's recency
window) on tickers that appear on any user's watchlist, and creates a
notification for each subscribed user -- the "Watchlist News"
subscription category. Distinct from watchlist_alerts.py (price moves)
and price_alerts.py (explicit price targets).
"""

from database.models import Watchlist
from database.database import db_manager
from logging_config import logger
from market_intelligence.news_classifier import classify_breaking_news
from market_intelligence.news_service import get_or_fetch_company_news
from market_intelligence.notification_service import create_notification, should_notify

# In-process de-dupe guard so the same headline doesn't spawn a second
# notification if the scheduler runs again before the news_cache TTL expires.
_already_notified_urls: set[str] = set()


def _get_watchlisted_tickers_by_user() -> dict[int, list[str]]:
    """Group every watchlist entry by user_id -> [ticker_symbol, ...]."""
    all_entries = db_manager.get_all(Watchlist, limit=5000)
    grouped: dict[int, list[str]] = {}
    for entry in all_entries:
        grouped.setdefault(entry.user_id, []).append(entry.ticker_symbol)
    return grouped


def check_watchlist_breaking_news() -> int:
    """
    Check every user's watchlist for breaking news and notify subscribed
    users. Intended to be invoked periodically by notification_scheduler.py.

    Returns:
        The number of notifications created during this run.
    """
    grouped = _get_watchlisted_tickers_by_user()
    if not grouped:
        return 0

    # Fetch each unique ticker's news only once per run, regardless of how
    # many users are watching it.
    unique_tickers = {ticker for tickers in grouped.values() for ticker in tickers}
    breaking_by_ticker = {
        ticker: classify_breaking_news(get_or_fetch_company_news(ticker, limit=8)) for ticker in unique_tickers
    }

    notified_count = 0
    for user_id, tickers in grouped.items():
        if not should_notify(user_id, "watchlist_news"):
            continue

        for ticker in tickers:
            for article in breaking_by_ticker.get(ticker, []):
                if article["url"] in _already_notified_urls:
                    continue

                create_notification(
                    user_id=user_id,
                    notification_type="WATCHLIST_NEWS",
                    title=f"Breaking: {ticker}",
                    message=article["headline"],
                    priority="MEDIUM",
                    related_ticker=ticker,
                )
                _already_notified_urls.add(article["url"])
                notified_count += 1

    if notified_count:
        logger.info(f"Watchlist news check complete: {notified_count} notification(s) created.")
    return notified_count
