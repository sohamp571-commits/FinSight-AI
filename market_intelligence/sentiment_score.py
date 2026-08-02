"""
market_intelligence/sentiment_score.py

Purpose: Aggregates individual `sentiment_analysis.SentimentResult`
objects (one per headline) into a single overall sentiment score for
a company, sector, or the whole market -- with a confidence score
reflecting both the volume and the agreement level of the underlying
articles. Used by market_sentiment.py, company_news.py, and
sector_news.py.
"""

from dataclasses import dataclass

from market_intelligence.news_parser import NormalizedArticle
from market_intelligence.sentiment_analysis import SentimentResult, analyze_headline

MINIMUM_ARTICLES_FOR_CONFIDENCE = 5


@dataclass
class AggregateSentiment:
    """An overall sentiment read aggregated across multiple articles."""

    average_polarity: float
    sentiment_label: str
    market_bias: str
    confidence: float
    positive_count: int
    neutral_count: int
    negative_count: int
    article_count: int


def score_articles(articles: list[NormalizedArticle]) -> list[tuple[NormalizedArticle, SentimentResult]]:
    """Run sentiment analysis on every article's headline, pairing each with its result."""
    return [(article, analyze_headline(article["headline"])) for article in articles]


def aggregate_sentiment(articles: list[NormalizedArticle]) -> AggregateSentiment:
    """
    Aggregate sentiment across a list of articles into one overall read.
    Returns a neutral, zero-confidence result if there are no articles.
    """
    if not articles:
        return AggregateSentiment(
            average_polarity=0.0, sentiment_label="Neutral", market_bias="Neutral",
            confidence=0.0, positive_count=0, neutral_count=0, negative_count=0, article_count=0,
        )

    scored = score_articles(articles)
    polarities = [result.polarity for _, result in scored]
    average_polarity = round(sum(polarities) / len(polarities), 4)

    positive_count = sum(1 for _, r in scored if r.sentiment_label == "Positive")
    negative_count = sum(1 for _, r in scored if r.sentiment_label == "Negative")
    neutral_count = len(scored) - positive_count - negative_count

    if average_polarity >= 0.1:
        sentiment_label = "Positive"
    elif average_polarity <= -0.1:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    bullish_count = sum(1 for _, r in scored if r.market_bias == "Bullish")
    bearish_count = sum(1 for _, r in scored if r.market_bias == "Bearish")
    if bullish_count > bearish_count:
        market_bias = "Bullish"
    elif bearish_count > bullish_count:
        market_bias = "Bearish"
    else:
        market_bias = "Neutral"

    # Confidence blends sample size (more articles = more reliable) with
    # agreement (low variance in polarity = more reliable).
    volume_factor = min(1.0, len(scored) / MINIMUM_ARTICLES_FOR_CONFIDENCE)
    variance = sum((p - average_polarity) ** 2 for p in polarities) / len(polarities)
    agreement_factor = max(0.0, 1.0 - variance)
    confidence = round(((volume_factor * 0.5) + (agreement_factor * 0.5)) * 100, 1)

    return AggregateSentiment(
        average_polarity=average_polarity,
        sentiment_label=sentiment_label,
        market_bias=market_bias,
        confidence=confidence,
        positive_count=positive_count,
        neutral_count=neutral_count,
        negative_count=negative_count,
        article_count=len(articles),
    )
