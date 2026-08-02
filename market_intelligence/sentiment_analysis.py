"""
market_intelligence/sentiment_analysis.py

Purpose: Computes sentiment for individual news headlines using
TextBlob (already in requirements.txt from Phase 1). Maps TextBlob's
polarity score onto both a general sentiment label (Positive/Neutral/
Negative) and a market-specific bullish/bearish read, since "positive
news" and "bullish news" aren't always the same axis for a trader.
"""

from dataclasses import dataclass

from textblob import TextBlob

POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1

# Domain-specific keywords that nudge a headline toward bullish/bearish
# beyond what generic sentence-level polarity alone would catch.
_BULLISH_KEYWORDS = (
    "surge", "rally", "soar", "gain", "beat estimates", "record high", "upgrade",
    "buyback", "profit rise", "outperform", "breakout", "all-time high",
)
_BEARISH_KEYWORDS = (
    "plunge", "crash", "slump", "downgrade", "miss estimates", "record low",
    "sell-off", "selloff", "loss", "layoffs", "probe", "lawsuit", "recall",
)


@dataclass
class SentimentResult:
    """Sentiment analysis result for a single piece of text."""

    polarity: float  # -1.0 (very negative) to +1.0 (very positive)
    subjectivity: float  # 0.0 (objective) to 1.0 (subjective)
    sentiment_label: str  # Positive / Neutral / Negative
    market_bias: str  # Bullish / Bearish / Neutral
    confidence: float  # 0-100


def analyze_text_sentiment(text: str) -> SentimentResult:
    """Run TextBlob sentiment analysis on a single string (typically a headline)."""
    blob = TextBlob(text)
    polarity = round(float(blob.sentiment.polarity), 4)
    subjectivity = round(float(blob.sentiment.subjectivity), 4)

    if polarity >= POSITIVE_THRESHOLD:
        sentiment_label = "Positive"
    elif polarity <= NEGATIVE_THRESHOLD:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    market_bias = _determine_market_bias(text, polarity)
    confidence = round(min(1.0, abs(polarity) + (subjectivity * 0.2)) * 100, 1)

    return SentimentResult(
        polarity=polarity,
        subjectivity=subjectivity,
        sentiment_label=sentiment_label,
        market_bias=market_bias,
        confidence=confidence,
    )


def _determine_market_bias(text: str, polarity: float) -> str:
    """Blend generic polarity with finance-specific keyword cues to get a bullish/bearish read."""
    lowered = text.lower()
    has_bullish_keyword = any(keyword in lowered for keyword in _BULLISH_KEYWORDS)
    has_bearish_keyword = any(keyword in lowered for keyword in _BEARISH_KEYWORDS)

    if has_bullish_keyword and not has_bearish_keyword:
        return "Bullish"
    if has_bearish_keyword and not has_bullish_keyword:
        return "Bearish"

    if polarity >= POSITIVE_THRESHOLD:
        return "Bullish"
    if polarity <= NEGATIVE_THRESHOLD:
        return "Bearish"
    return "Neutral"


def analyze_headline(headline: str) -> SentimentResult:
    """Convenience alias for analyzing a single news headline."""
    return analyze_text_sentiment(headline)
