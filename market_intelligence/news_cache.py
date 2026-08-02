"""
market_intelligence/news_cache.py

Purpose: Bridges news_fetcher.py (external APIs) and the *existing*
`news_cache` database table (Phase 1 schema, Phase 3
`database.news_service`) -- reused here exactly as instructed, with
no new table. Checks whether sufficiently fresh cached articles
already exist in the database before calling out to yfinance/NewsAPI
again, and persists newly-fetched articles back to the same table.
"""

from datetime import datetime, timedelta

from custom_exceptions import DatabaseQueryError
from database.news_service import news_service
from logging_config import logger
from market_intelligence.news_fetcher import fetch_company_news
from market_intelligence.news_parser import NormalizedArticle

CACHE_FRESHNESS_MINUTES = 30


def _row_to_article(row) -> NormalizedArticle:
    """Convert a `NewsCache` ORM row back into the normalized article dict shape."""
    return {
        "headline": row.headline,
        "source": row.source,
        "url": row.url,
        "published_at": row.published_at,
        "ticker_symbol": row.ticker_symbol,
        "sentiment_score": float(row.sentiment_score) if row.sentiment_score is not None else None,
    }


def get_cached_company_news(ticker: str, limit: int = 10) -> list[NormalizedArticle]:
    """Return cached news for a ticker from the database if fresh, else None."""
    try:
        result = news_service.get_news_for_ticker(ticker, page_size=limit)
    except DatabaseQueryError as exc:
        logger.error(f"Failed to read cached news for {ticker}: {exc}")
        return []

    if not result["items"]:
        return []

    newest_fetched = max((row.fetched_at for row in result["items"]), default=None)
    if newest_fetched is None or datetime.utcnow() - newest_fetched > timedelta(minutes=CACHE_FRESHNESS_MINUTES):
        return []  # stale -- caller should refresh

    return [_row_to_article(row) for row in result["items"]]


def get_or_fetch_company_news(
    ticker: str, limit: int = 10, sentiment_scores: dict[str, float] | None = None
) -> list[NormalizedArticle]:
    """
    Return fresh cached news for a ticker if available, otherwise fetch
    from news_fetcher.py and persist the results to `news_cache`.

    Args:
        sentiment_scores: optional {url: score} map to attach before persisting
            (populated by sentiment_analysis.py in the news_service.py orchestrator).
    """
    cached = get_cached_company_news(ticker, limit)
    if cached:
        return cached

    fresh_articles = fetch_company_news(ticker, limit)
    if not fresh_articles:
        return []

    sentiment_scores = sentiment_scores or {}
    try:
        news_service.bulk_cache_articles(
            [
                {
                    "ticker_symbol": article["ticker_symbol"],
                    "headline": article["headline"],
                    "source": article["source"],
                    "url": article["url"],
                    "sentiment_score": sentiment_scores.get(article["url"]),
                    "published_at": article["published_at"],
                }
                for article in fresh_articles
            ]
        )
        logger.info(f"Cached {len(fresh_articles)} fresh article(s) for {ticker}.")
    except DatabaseQueryError as exc:
        logger.error(f"Failed to persist fresh news for {ticker} to cache: {exc}")

    return fresh_articles
