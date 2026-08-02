"""
market_intelligence/news_classifier.py

Purpose: Classifies a set of articles into "Breaking News" (published
very recently) versus regular news, and detects trending stocks/sectors
by counting article mentions across the tracked universe -- powering
the Trending Stocks / Trending Sectors / Breaking News requirements
without needing a separate ML model for something this can solve with
straightforward counting and recency thresholds.
"""

from collections import Counter
from datetime import datetime, timedelta

from market_intelligence.news_parser import NormalizedArticle

BREAKING_NEWS_WINDOW_HOURS = 3


def classify_breaking_news(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    """Return the subset of articles published within the breaking-news recency window."""
    cutoff = datetime.utcnow() - timedelta(hours=BREAKING_NEWS_WINDOW_HOURS)
    return [a for a in articles if a["published_at"] and a["published_at"] >= cutoff]


def detect_trending_stocks(articles_by_ticker: dict[str, list[NormalizedArticle]], top_n: int = 10) -> list[tuple[str, int]]:
    """
    Rank tickers by news volume (article count) as a simple, transparent
    proxy for "trending" -- more coverage in a short window suggests
    more market attention.

    Args:
        articles_by_ticker: {ticker: [articles...]}

    Returns:
        [(ticker, article_count), ...] sorted descending, top_n entries.
    """
    counts = Counter({ticker: len(articles) for ticker, articles in articles_by_ticker.items()})
    return counts.most_common(top_n)


def detect_trending_sectors(
    articles_by_ticker: dict[str, list[NormalizedArticle]], ticker_to_sector: dict[str, str], top_n: int = 8
) -> list[tuple[str, int]]:
    """
    Rank sectors by aggregated news volume across their constituent
    tickers.

    Args:
        articles_by_ticker: {ticker: [articles...]}
        ticker_to_sector: {ticker: sector_name} mapping (see sector_news.py)

    Returns:
        [(sector_name, article_count), ...] sorted descending, top_n entries.
    """
    sector_counts: Counter[str] = Counter()
    for ticker, articles in articles_by_ticker.items():
        sector = ticker_to_sector.get(ticker, "Other")
        sector_counts[sector] += len(articles)
    return sector_counts.most_common(top_n)


def summarize_news_batch(articles: list[NormalizedArticle], max_headlines: int = 5) -> str:
    """
    Build a short, deterministic "AI News Summary" string from a batch
    of headlines -- the most recent `max_headlines` headlines joined as
    a digest, since generating this via a live LLM call is out of scope
    for this module (no such API is configured in the project).
    """
    if not articles:
        return "No recent news available to summarize."

    top_headlines = articles[:max_headlines]
    bullet_lines = "\n".join(f"• {a['headline']}" for a in top_headlines)
    return f"Here are the {len(top_headlines)} most recent headlines:\n{bullet_lines}"
