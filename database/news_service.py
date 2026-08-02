"""
database/news_service.py

Purpose: Data-layer service for the `news_cache` table -- stores news
headlines fetched from NewsAPI along with a sentiment score, so the
`news` feature module (later phase) doesn't have to hit the external
API on every page load. This phase provides caching/query primitives
only; the NewsAPI/TextBlob integration itself belongs to that module.
"""

from datetime import datetime
from typing import Any

from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import NewsCache
from logging_config import logger


class NewsService(BaseService[NewsCache]):
    """CRUD and cache-management operations for the `news_cache` table."""

    model = NewsCache
    pk_column = "news_id"

    def cache_article(
        self,
        headline: str,
        url: str,
        ticker_symbol: str | None = None,
        source: str | None = None,
        sentiment_score: float | None = None,
        published_at: datetime | None = None,
    ) -> NewsCache:
        """Persist a single fetched news article."""
        if not headline.strip() or not url.strip():
            raise ValidationError("headline and url are required.")
        if sentiment_score is not None and not (-1.0 <= sentiment_score <= 1.0):
            raise ValidationError("sentiment_score must be between -1.0 and 1.0.")

        entry = NewsCache(
            ticker_symbol=ticker_symbol.strip().upper() if ticker_symbol else None,
            headline=headline.strip(),
            source=source.strip() if source else None,
            url=url.strip(),
            sentiment_score=sentiment_score,
            published_at=published_at,
        )
        created = self.create(entry)
        logger.info(f"News article cached: ticker={ticker_symbol}, source={source}")
        return created

    def bulk_cache_articles(self, articles: list[dict[str, Any]]) -> list[NewsCache]:
        """Bulk-insert a batch of fetched articles (e.g. a full NewsAPI response page)."""
        entries = [
            NewsCache(
                ticker_symbol=(a.get("ticker_symbol") or "").strip().upper() or None,
                headline=a["headline"].strip(),
                source=(a.get("source") or "").strip() or None,
                url=a["url"].strip(),
                sentiment_score=a.get("sentiment_score"),
                published_at=a.get("published_at"),
            )
            for a in articles
        ]
        created = self.bulk_create(entries)
        logger.info(f"Bulk-cached {len(created)} news article(s).")
        return created

    def get_news_for_ticker(self, ticker_symbol: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """List cached news for a specific ticker, most recently published first."""
        return self.list(
            filters={"ticker_symbol": ticker_symbol.strip().upper()},
            sort_by="published_at",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )

    def search_news(self, search_term: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """Search cached news headlines by keyword."""
        return self.list(
            search_term=search_term,
            search_columns=["headline"],
            sort_by="published_at",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )


news_service = NewsService()
