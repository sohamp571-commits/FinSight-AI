"""
market_intelligence/news_service.py

Purpose: The Streamlit-free orchestration layer for news -- combines
news_cache.py (fetch-or-cache), sentiment_score.py (aggregate
sentiment), and news_classifier.py (breaking/trending) into the
handful of high-level functions that company_news.py, sector_news.py,
global_market_news.py, and news_dashboard.py actually call. Mirrors
the role `authentication.auth_service.AuthService` and
`stock_search.search_service` play in their own packages.
"""

from dashboard.market_data_service import NIFTY50_UNIVERSE
from market_intelligence.news_cache import get_or_fetch_company_news
from market_intelligence.news_classifier import classify_breaking_news, detect_trending_stocks, summarize_news_batch
from market_intelligence.news_fetcher import fetch_global_market_news
from market_intelligence.news_parser import NormalizedArticle, deduplicate_articles, sort_articles_by_recency
from market_intelligence.sentiment_score import AggregateSentiment, aggregate_sentiment

# A lightweight static sector map for the tracked universe, since
# yfinance's per-ticker `.info` sector lookup for 30 tickers on every
# render would be far too slow for a news feed -- this mirrors the
# same "own small static directory" approach already used by
# stock_search.search_service.COMPANY_DIRECTORY.
SECTOR_MAP: dict[str, str] = {
    "RELIANCE.NS": "Energy", "ONGC.NS": "Energy", "NTPC.NS": "Energy", "POWERGRID.NS": "Energy",
    "TCS.NS": "IT", "INFY.NS": "IT", "WIPRO.NS": "IT", "HCLTECH.NS": "IT", "TECHM.NS": "IT",
    "HDFCBANK.NS": "Banking", "ICICIBANK.NS": "Banking", "SBIN.NS": "Banking",
    "KOTAKBANK.NS": "Banking", "AXISBANK.NS": "Banking",
    "ITC.NS": "FMCG", "HINDUNILVR.NS": "FMCG", "NESTLEIND.NS": "FMCG",
    "BHARTIARTL.NS": "Telecom",
    "LT.NS": "Infrastructure", "ULTRACEMCO.NS": "Infrastructure",
    "ASIANPAINT.NS": "Consumer Goods", "TITAN.NS": "Consumer Goods",
    "MARUTI.NS": "Automobile", "TATAMOTORS.NS": "Automobile", "M&M.NS": "Automobile",
    "SUNPHARMA.NS": "Pharma",
    "BAJFINANCE.NS": "Financial Services",
    "TATASTEEL.NS": "Metals", "JSWSTEEL.NS": "Metals",
    "ADANIENT.NS": "Conglomerate",
}


def get_company_news_with_sentiment(ticker: str, limit: int = 10) -> tuple[list[NormalizedArticle], AggregateSentiment]:
    """Fetch (or reuse cached) news for a ticker, score its sentiment article-by-article, and aggregate."""
    articles = get_or_fetch_company_news(ticker, limit)
    overall = aggregate_sentiment(articles)
    return articles, overall


def get_sector_news_with_sentiment(sector_name: str, limit_per_ticker: int = 4) -> tuple[list[NormalizedArticle], AggregateSentiment]:
    """Aggregate news + sentiment across every ticker belonging to a given sector."""
    sector_tickers = [ticker for ticker, sector in SECTOR_MAP.items() if sector == sector_name]
    all_articles: list[NormalizedArticle] = []
    for ticker in sector_tickers:
        all_articles.extend(get_or_fetch_company_news(ticker, limit_per_ticker))

    deduped = sort_articles_by_recency(deduplicate_articles(all_articles))
    overall = aggregate_sentiment(deduped)
    return deduped, overall


def get_global_market_news_with_sentiment(limit: int = 15) -> tuple[list[NormalizedArticle], AggregateSentiment]:
    """Fetch broad global market news and its aggregate sentiment."""
    articles = fetch_global_market_news(limit)
    overall = aggregate_sentiment(articles)
    return articles, overall


def get_live_market_news(limit: int = 20) -> list[NormalizedArticle]:
    """
    Build a 'Live Market News' feed spanning a handful of large-cap
    tickers from the tracked universe, for a general market pulse view.
    """
    all_articles: list[NormalizedArticle] = []
    for ticker in list(NIFTY50_UNIVERSE.keys())[:8]:
        all_articles.extend(get_or_fetch_company_news(ticker, limit=4))

    return sort_articles_by_recency(deduplicate_articles(all_articles))[:limit]


def get_breaking_news(limit: int = 10) -> list[NormalizedArticle]:
    """Return only the most recently published articles across the live market feed."""
    live_feed = get_live_market_news(limit=40)
    return classify_breaking_news(live_feed)[:limit]


def get_trending_stocks(top_n: int = 10) -> list[tuple[str, int]]:
    """Rank the tracked universe's tickers by recent news volume."""
    articles_by_ticker = {ticker: get_or_fetch_company_news(ticker, limit=5) for ticker in NIFTY50_UNIVERSE}
    return detect_trending_stocks(articles_by_ticker, top_n)


def get_ai_news_summary(limit: int = 5) -> str:
    """Build a short digest-style summary of the latest live market news."""
    return summarize_news_batch(get_live_market_news(limit=20), max_headlines=limit)
