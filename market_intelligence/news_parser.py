"""
market_intelligence/news_parser.py

Purpose: Normalizes raw news payloads from different sources (yfinance's
`Ticker.news`, NewsAPI's article schema) into one consistent internal
shape used throughout `market_intelligence/`. Keeping this in one place
means every other file (news_fetcher.py, news_cache.py, sentiment_analysis.py)
works with a single, predictable article dict regardless of where it
came from.
"""

from datetime import datetime, timezone
from typing import Any

NormalizedArticle = dict[str, Any]
# Canonical shape: {"headline": str, "source": str | None, "url": str,
#                    "published_at": datetime | None, "ticker_symbol": str | None}


def parse_yfinance_article(raw: dict[str, Any], ticker_symbol: str | None = None) -> NormalizedArticle | None:
    """Normalize a single item from `yfinance.Ticker(ticker).news`."""
    content = raw.get("content", raw)  # yfinance has nested "content" in newer versions
    headline = content.get("title") or raw.get("title")
    url = (content.get("canonicalUrl") or {}).get("url") or content.get("clickThroughUrl", {}).get("url") or raw.get("link")

    if not headline or not url:
        return None

    published_raw = content.get("pubDate") or raw.get("providerPublishTime")
    published_at = _parse_timestamp(published_raw)

    source = (content.get("provider") or {}).get("displayName") or raw.get("publisher") or "Yahoo Finance"

    return {
        "headline": headline.strip(),
        "source": source,
        "url": url,
        "published_at": published_at,
        "ticker_symbol": ticker_symbol,
    }


def parse_newsapi_article(raw: dict[str, Any], ticker_symbol: str | None = None) -> NormalizedArticle | None:
    """Normalize a single article from a NewsAPI `/v2/everything` or `/v2/top-headlines` response."""
    headline = raw.get("title")
    url = raw.get("url")
    if not headline or not url:
        return None

    published_at = _parse_timestamp(raw.get("publishedAt"))
    source = (raw.get("source") or {}).get("name", "Unknown Source")

    return {
        "headline": headline.strip(),
        "source": source,
        "url": url,
        "published_at": published_at,
        "ticker_symbol": ticker_symbol,
    }


def _parse_timestamp(value: Any) -> datetime | None:
    """Best-effort conversion of a timestamp (ISO string or unix epoch) into a naive UTC datetime."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        if isinstance(value, str):
            cleaned = value.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned).replace(tzinfo=None)
    except (ValueError, OverflowError, OSError):
        return None
    return None


def deduplicate_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    """Remove duplicate articles (same URL) while preserving order."""
    seen_urls: set[str] = set()
    deduped: list[NormalizedArticle] = []
    for article in articles:
        if article["url"] in seen_urls:
            continue
        seen_urls.add(article["url"])
        deduped.append(article)
    return deduped


def sort_articles_by_recency(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    """Sort articles newest-first, pushing articles with an unknown publish time to the end."""
    return sorted(articles, key=lambda a: a["published_at"] or datetime.min, reverse=True)
