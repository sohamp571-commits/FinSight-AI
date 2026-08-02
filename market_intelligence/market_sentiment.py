"""
market_intelligence/market_sentiment.py

Purpose: Computes an overall "Market Sentiment" read by combining
news-derived sentiment (via news_service.py/sentiment_score.py) across
the tracked universe with actual price action (via
dashboard.market_data_service, Phase 4 reuse) -- since sentiment
divorced from price movement is a weaker signal than the two combined.
"""

from dataclasses import dataclass

from dashboard.market_data_service import NIFTY50_UNIVERSE, get_universe_quotes
from market_intelligence.news_service import get_live_market_news
from market_intelligence.sentiment_score import AggregateSentiment, aggregate_sentiment


@dataclass
class MarketSentimentReport:
    """A combined news-sentiment + price-action read of overall market mood."""

    news_sentiment: AggregateSentiment
    advancing_count: int
    declining_count: int
    unchanged_count: int
    breadth_pct: float  # % of tracked universe that's up today
    overall_mood: str  # Bullish / Bearish / Neutral / Mixed


def compute_market_breadth() -> tuple[int, int, int, float]:
    """Compute how many tracked tickers are up/down/flat today (market breadth)."""
    quotes = get_universe_quotes()
    advancing = sum(1 for q in quotes.values() if q["change_pct"] > 0)
    declining = sum(1 for q in quotes.values() if q["change_pct"] < 0)
    unchanged = len(quotes) - advancing - declining
    breadth_pct = round((advancing / len(quotes)) * 100, 1) if quotes else 0.0
    return advancing, declining, unchanged, breadth_pct


def compute_market_sentiment() -> MarketSentimentReport:
    """Compute the full combined market sentiment report."""
    news_articles = get_live_market_news(limit=40)
    news_sentiment = aggregate_sentiment(news_articles)
    advancing, declining, unchanged, breadth_pct = compute_market_breadth()

    news_bullish = news_sentiment.market_bias == "Bullish"
    news_bearish = news_sentiment.market_bias == "Bearish"
    price_bullish = breadth_pct >= 55
    price_bearish = breadth_pct <= 45

    if news_bullish and price_bullish:
        overall_mood = "Bullish"
    elif news_bearish and price_bearish:
        overall_mood = "Bearish"
    elif news_bullish != price_bullish and (news_bullish or price_bullish):
        overall_mood = "Mixed"
    else:
        overall_mood = "Neutral"

    return MarketSentimentReport(
        news_sentiment=news_sentiment,
        advancing_count=advancing,
        declining_count=declining,
        unchanged_count=unchanged,
        breadth_pct=breadth_pct,
        overall_mood=overall_mood,
    )
