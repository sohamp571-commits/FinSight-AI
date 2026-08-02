"""
portfolio/recommendation_engine.py

Purpose: The cross-module integration point Phase 9 calls for --
generates a per-holding recommendation by combining three existing
signal sources, reusing each one's own logic with zero duplication:
    - Technical Analysis (Phase 6): analytics.signal_generator's
      indicator-based BUY/SELL/NEUTRAL votes
    - Machine Learning (Phase 7): the user's most recent cached
      prediction for that ticker (via machine_learning.prediction_history
      -- does NOT trigger a fresh training run on every dashboard
      render, which would be far too slow; the user generates
      predictions from the ML Prediction page and this module simply
      reads the latest one)
    - Market Intelligence (Phase 8): market_intelligence.news_service's
      aggregate news sentiment for that ticker
"""

from dataclasses import dataclass

from analytics.indicator_service import get_ohlcv, has_sufficient_data
from analytics.signal_generator import generate_signals, get_overall_recommendation
from machine_learning.prediction_history import get_ticker_prediction_history
from market_intelligence.news_service import get_company_news_with_sentiment

DEFAULT_TIMEFRAME = "6 Month"


@dataclass
class HoldingRecommendation:
    """A single holding's combined recommendation and the evidence behind it."""

    ticker: str
    overall_recommendation: str  # BUY MORE / HOLD / CONSIDER SELLING
    technical_signal: str | None
    ml_prediction_change_pct: float | None
    ml_prediction_available: bool
    sentiment_label: str | None
    sentiment_bias: str | None
    reasoning: list[str]


def _get_technical_signal(ticker: str) -> str | None:
    """Reuse analytics.signal_generator for this ticker's overall technical read."""
    df = get_ohlcv(ticker, DEFAULT_TIMEFRAME)
    if not has_sufficient_data(df, minimum_bars=30):
        return None
    signals = generate_signals(df)
    overall, _, _, _ = get_overall_recommendation(signals)
    return overall


def _get_latest_ml_prediction_change(user_id: int, ticker: str, current_price: float) -> float | None:
    """Reuse the user's most recent cached ML prediction for this ticker, if one exists."""
    history = get_ticker_prediction_history(user_id, ticker, limit=1)
    if not history:
        return None
    latest = history[0]
    predicted_price = float(latest.predicted_price)
    if current_price == 0:
        return None
    return round(((predicted_price - current_price) / current_price) * 100, 2)


def _combine_into_recommendation(
    technical_signal: str | None, ml_change_pct: float | None, sentiment_bias: str | None
) -> tuple[str, list[str]]:
    """Blend the three signals into one overall recommendation with a plain-English reasoning trail."""
    reasoning: list[str] = []
    bullish_votes = 0
    bearish_votes = 0

    if technical_signal == "BUY":
        bullish_votes += 1
        reasoning.append("Technical indicators are net bullish.")
    elif technical_signal == "SELL":
        bearish_votes += 1
        reasoning.append("Technical indicators are net bearish.")
    elif technical_signal is not None:
        reasoning.append("Technical indicators are neutral.")

    if ml_change_pct is not None:
        if ml_change_pct >= 3:
            bullish_votes += 1
            reasoning.append(f"ML prediction implies {ml_change_pct:+.2f}% upside.")
        elif ml_change_pct <= -3:
            bearish_votes += 1
            reasoning.append(f"ML prediction implies {ml_change_pct:+.2f}% downside.")
        else:
            reasoning.append(f"ML prediction implies a modest {ml_change_pct:+.2f}% move.")
    else:
        reasoning.append("No recent ML prediction available for this ticker.")

    if sentiment_bias == "Bullish":
        bullish_votes += 1
        reasoning.append("Recent news sentiment is bullish.")
    elif sentiment_bias == "Bearish":
        bearish_votes += 1
        reasoning.append("Recent news sentiment is bearish.")
    elif sentiment_bias is not None:
        reasoning.append("Recent news sentiment is neutral.")

    if bullish_votes > bearish_votes:
        overall = "BUY MORE"
    elif bearish_votes > bullish_votes:
        overall = "CONSIDER SELLING"
    else:
        overall = "HOLD"

    return overall, reasoning


def generate_holding_recommendation(user_id: int, ticker: str, current_price: float) -> HoldingRecommendation:
    """Generate a full combined recommendation for a single holding."""
    technical_signal = _get_technical_signal(ticker)
    ml_change_pct = _get_latest_ml_prediction_change(user_id, ticker, current_price)

    _, sentiment = get_company_news_with_sentiment(ticker, limit=10)
    sentiment_label = sentiment.sentiment_label if sentiment.article_count > 0 else None
    sentiment_bias = sentiment.market_bias if sentiment.article_count > 0 else None

    overall, reasoning = _combine_into_recommendation(technical_signal, ml_change_pct, sentiment_bias)

    return HoldingRecommendation(
        ticker=ticker,
        overall_recommendation=overall,
        technical_signal=technical_signal,
        ml_prediction_change_pct=ml_change_pct,
        ml_prediction_available=ml_change_pct is not None,
        sentiment_label=sentiment_label,
        sentiment_bias=sentiment_bias,
        reasoning=reasoning,
    )


def generate_portfolio_recommendations(user_id: int, holdings: list[dict]) -> list[HoldingRecommendation]:
    """Generate recommendations for every holding in a portfolio summary."""
    return [
        generate_holding_recommendation(user_id, holding["ticker_symbol"], holding["current_price"])
        for holding in holdings
    ]
