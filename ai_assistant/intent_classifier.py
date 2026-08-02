"""
ai_assistant/intent_classifier.py

Purpose: Classifies a user's natural-language question into one of a
fixed set of intents (Portfolio, Watchlist, News, Sentiment, IPO,
Notifications, Company, Technical, Prediction, General) using simple
keyword matching. This is deliberately rule-based rather than an LLM
call -- it needs to work identically whether or not an API key is
configured, and it's the mechanism that decides *which* existing
service `context_builder.py` should call, so a wrong guess just means
slightly less-relevant context, never a crash.
"""

from dataclasses import dataclass

INTENT_PORTFOLIO = "PORTFOLIO"
INTENT_WATCHLIST = "WATCHLIST"
INTENT_NEWS = "NEWS"
INTENT_SENTIMENT = "SENTIMENT"
INTENT_IPO = "IPO"
INTENT_NOTIFICATIONS = "NOTIFICATIONS"
INTENT_COMPANY = "COMPANY"
INTENT_TECHNICAL = "TECHNICAL"
INTENT_PREDICTION = "PREDICTION"
INTENT_RECOMMENDATION = "RECOMMENDATION"
INTENT_GENERAL = "GENERAL"

_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    INTENT_PORTFOLIO: ("portfolio", "my holdings", "my investment", "profit", "loss", "p&l", "diversif", "allocation", "risk score", "health score", "dividend"),
    INTENT_WATCHLIST: ("watchlist", "watch list", "tracking", "favorites", "favourite"),
    INTENT_NEWS: ("news", "headline", "article", "breaking"),
    INTENT_SENTIMENT: ("sentiment", "mood", "market feel", "bullish", "bearish"),
    INTENT_IPO: ("ipo", "listing", "subscription", "gmp", "grey market"),
    INTENT_NOTIFICATIONS: ("notification", "alert", "unread"),
    INTENT_RECOMMENDATION: ("should i buy", "should i sell", "recommend", "worth buying", "good investment", "buy more", "sell my"),
    INTENT_TECHNICAL: ("rsi", "macd", "bollinger", "moving average", "technical", "trend", "support", "resistance", "indicator", "adx", "stochastic"),
    INTENT_PREDICTION: ("predict", "forecast", "future price", "ml model", "target price"),
    INTENT_COMPANY: ("about", "sector", "industry", "ceo", "market cap", "pe ratio", "eps", "profile", "what is", "who is"),
}


@dataclass
class ClassifiedIntent:
    """The detected intent plus any ticker-like token extracted from the question."""

    intent: str
    raw_question: str


def classify_intent(question: str) -> ClassifiedIntent:
    """
    Classify a question into one intent. Checks recommendation/technical/
    prediction/IPO/notification intents before the broader portfolio/company
    buckets, since phrases like "should I buy more X" would otherwise also
    match the generic "buy"/company-related keywords.
    """
    lowered = question.lower().strip()

    priority_order = (
        INTENT_RECOMMENDATION, INTENT_TECHNICAL, INTENT_PREDICTION, INTENT_IPO,
        INTENT_NOTIFICATIONS, INTENT_SENTIMENT, INTENT_NEWS, INTENT_WATCHLIST,
        INTENT_PORTFOLIO, INTENT_COMPANY,
    )

    for intent in priority_order:
        keywords = _INTENT_KEYWORDS[intent]
        if any(keyword in lowered for keyword in keywords):
            return ClassifiedIntent(intent=intent, raw_question=question)

    return ClassifiedIntent(intent=INTENT_GENERAL, raw_question=question)
