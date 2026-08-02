"""
market_intelligence/news_fetcher.py

Purpose: The only module in `market_intelligence/` that calls external
news sources. Uses `yfinance.Ticker.news` (no API key required, and
consistent with the Phase 7 instruction to reuse the existing
yfinance service) as the primary source for company news, and
NewsAPI (via `config.NEWS_API_KEY`, already provisioned in Phase 1's
`.env.example`) as an optional secondary source for sector/global
news when a key is configured. Falls back gracefully -- with a
logged warning, never a crash -- when NewsAPI isn't configured.
"""

import time
from typing import Any

import requests
import streamlit as st
import yfinance as yf

from config import config
from custom_exceptions import ExternalAPIError
from logging_config import logger
from market_intelligence.news_parser import (
    NormalizedArticle,
    deduplicate_articles,
    parse_newsapi_article,
    parse_yfinance_article,
    sort_articles_by_recency,
)

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.5
_CACHE_TTL_SECONDS = 900  # 15 minutes -- news doesn't need per-second freshness
NEWSAPI_BASE_URL = "https://newsapi.org/v2"


def _retry(callable_fn, *args, **kwargs) -> Any:
    """Shared retry helper, matching the pattern used across every other data-fetching module."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return callable_fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"News fetch attempt {attempt}/{_MAX_RETRIES} failed: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"News fetch failed after {_MAX_RETRIES} attempts: {last_exc}")
    raise ExternalAPIError(f"Failed to fetch news: {last_exc}")


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_company_news(ticker: str, limit: int = 10) -> list[NormalizedArticle]:
    """Fetch recent news for a specific ticker via yfinance (no API key required)."""
    try:
        def _fetch() -> list[dict]:
            return yf.Ticker(ticker).news or []

        raw_items = _retry(_fetch)
    except ExternalAPIError:
        return []

    articles = [parse_yfinance_article(item, ticker_symbol=ticker) for item in raw_items]
    articles = [a for a in articles if a is not None]
    return sort_articles_by_recency(deduplicate_articles(articles))[:limit]


def is_newsapi_configured() -> bool:
    """Whether a NewsAPI key is present in configuration."""
    return bool(config.NEWS_API_KEY)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_newsapi_articles(query: str, limit: int = 15) -> list[NormalizedArticle]:
    """
    Fetch articles matching a free-text query via NewsAPI. Returns an
    empty list (with a logged warning, not an exception) if no API key
    is configured, so callers can always fall back to yfinance-sourced
    news without special-casing.
    """
    if not is_newsapi_configured():
        logger.warning("NEWS_API_KEY is not configured; skipping NewsAPI fetch.")
        return []

    try:
        def _fetch() -> dict:
            response = requests.get(
                f"{NEWSAPI_BASE_URL}/everything",
                params={
                    "q": query,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": limit,
                    "apiKey": config.NEWS_API_KEY,
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

        payload = _retry(_fetch)
    except ExternalAPIError:
        return []

    raw_articles = payload.get("articles", [])
    articles = [parse_newsapi_article(item) for item in raw_articles]
    articles = [a for a in articles if a is not None]
    return sort_articles_by_recency(deduplicate_articles(articles))[:limit]


def fetch_global_market_news(limit: int = 15) -> list[NormalizedArticle]:
    """
    Fetch broad global-market news. Prefers NewsAPI (a real "top
    business headlines" feed) when configured; otherwise aggregates
    yfinance news from the major indices as a no-key fallback.
    """
    if is_newsapi_configured():
        articles = fetch_newsapi_articles("stock market OR global markets OR economy", limit=limit)
        if articles:
            return articles

    from dashboard.market_data_service import MARKET_INDICES

    aggregated: list[NormalizedArticle] = []
    for ticker in list(MARKET_INDICES.values())[:3]:
        aggregated.extend(fetch_company_news(ticker, limit=5))

    return sort_articles_by_recency(deduplicate_articles(aggregated))[:limit]
