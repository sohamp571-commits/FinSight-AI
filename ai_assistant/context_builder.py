"""
ai_assistant/context_builder.py

Purpose: The heart of Phase 10's "no duplicate calculations" requirement.
For a classified intent, this module calls existing services from
every prior phase and returns a plain dict of facts -- it never
recomputes anything a service already provides. `rule_based_responder.py`
turns this dict into a templated answer directly; `prompt_builder.py`
turns it into an LLM prompt when an API key is configured. Either way,
the underlying facts come from exactly one place.
"""

from typing import Any

from ai_assistant.intent_classifier import (
    INTENT_COMPANY,
    INTENT_IPO,
    INTENT_NEWS,
    INTENT_NOTIFICATIONS,
    INTENT_PORTFOLIO,
    INTENT_PREDICTION,
    INTENT_RECOMMENDATION,
    INTENT_SENTIMENT,
    INTENT_TECHNICAL,
    INTENT_WATCHLIST,
    ClassifiedIntent,
)
from custom_exceptions import FinSightBaseException
from logging_config import logger


def extract_ticker_from_question(question: str) -> str | None:
    """
    Best-effort extraction of a ticker/company mention from free text,
    using only local (no-network) lookups against
    `stock_search.search_service`'s existing company directory and
    fuzzy-suggestion logic -- reused, not reimplemented.
    """
    from stock_search.search_service import COMPANY_DIRECTORY, get_autocomplete_suggestions

    words = [w.strip(".,?!'\"") for w in question.split()]
    candidates = words + [f"{a} {b}" for a, b in zip(words, words[1:])]

    for candidate in candidates:
        upper = candidate.upper()
        if upper in COMPANY_DIRECTORY or f"{upper}.NS" in COMPANY_DIRECTORY or f"{upper}.BO" in COMPANY_DIRECTORY:
            return upper if upper in COMPANY_DIRECTORY else (f"{upper}.NS" if f"{upper}.NS" in COMPANY_DIRECTORY else f"{upper}.BO")

    for candidate in candidates:
        if len(candidate) < 3:
            continue
        suggestions = get_autocomplete_suggestions(candidate, limit=1)
        if suggestions:
            return suggestions[0]["ticker"]

    return None


def build_context(user_id: int, classified: ClassifiedIntent) -> dict[str, Any]:
    """
    Build a fact dict for a classified intent by calling the relevant
    existing service(s). Every branch degrades gracefully (returns an
    "unavailable" note instead of raising) so a data-layer hiccup never
    breaks the conversation.
    """
    intent = classified.intent
    try:
        if intent == INTENT_PORTFOLIO:
            return _build_portfolio_context(user_id)
        if intent == INTENT_WATCHLIST:
            return _build_watchlist_context(user_id)
        if intent == INTENT_NEWS:
            return _build_news_context(classified.raw_question)
        if intent == INTENT_SENTIMENT:
            return _build_sentiment_context(classified.raw_question)
        if intent == INTENT_IPO:
            return _build_ipo_context()
        if intent == INTENT_NOTIFICATIONS:
            return _build_notifications_context(user_id)
        if intent == INTENT_COMPANY:
            return _build_company_context(classified.raw_question)
        if intent == INTENT_TECHNICAL:
            return _build_technical_context(classified.raw_question)
        if intent == INTENT_PREDICTION:
            return _build_prediction_context(user_id, classified.raw_question)
        if intent == INTENT_RECOMMENDATION:
            return _build_recommendation_context(user_id, classified.raw_question)
        return {"note": "No specific data domain matched; answering generally."}
    except FinSightBaseException as exc:
        logger.error(f"Context builder failed for intent={intent}: {exc}")
        return {"error": f"Could not retrieve data right now: {exc.message}"}
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected context builder failure for intent={intent}: {exc}")
        return {"error": "Could not retrieve data right now."}


def _build_portfolio_context(user_id: int) -> dict[str, Any]:
    from portfolio.allocation_analysis import compute_asset_allocation
    from portfolio.portfolio_calculator import compute_portfolio_overview
    from portfolio.portfolio_service import get_portfolio_summary_live, get_top_winner_and_loser
    from portfolio.risk_analysis import compute_risk_report

    overview = compute_portfolio_overview(user_id)
    allocation = compute_asset_allocation(user_id)
    risk = compute_risk_report(user_id)
    top_winner, top_loser = get_top_winner_and_loser(user_id)
    summary = get_portfolio_summary_live(user_id)

    return {
        "domain": "portfolio",
        "total_investment": overview.total_investment,
        "current_value": overview.current_value,
        "total_profit_loss": overview.total_profit_loss,
        "total_profit_loss_pct": overview.total_profit_loss_pct,
        "todays_gain_loss": overview.todays_gain_loss,
        "holdings_count": overview.holdings_count,
        "diversification_score": allocation.diversification_score,
        "concentration_label": allocation.concentration_label,
        "risk_score": risk.risk_score,
        "risk_label": risk.risk_label,
        "health_score": risk.health_score,
        "health_label": risk.health_label,
        "top_winner": top_winner["ticker_symbol"] if top_winner else None,
        "top_winner_pct": top_winner["profit_loss_pct"] if top_winner else None,
        "top_loser": top_loser["ticker_symbol"] if top_loser else None,
        "top_loser_pct": top_loser["profit_loss_pct"] if top_loser else None,
        "holdings": [{"ticker": h["ticker_symbol"], "pnl_pct": h["profit_loss_pct"]} for h in summary["holdings"]],
    }


def _build_watchlist_context(user_id: int) -> dict[str, Any]:
    from database.watchlist_service import watchlist_service
    from market_intelligence.watchlist_alerts import get_watchlist_movers_for_user

    entries = watchlist_service.list_watchlist(user_id, page_size=50)["items"]
    movers = get_watchlist_movers_for_user(user_id)

    return {
        "domain": "watchlist",
        "tickers": [e.ticker_symbol for e in entries],
        "count": len(entries),
        "movers": movers[:5],
    }


def _build_news_context(question: str) -> dict[str, Any]:
    from market_intelligence.news_service import get_company_news_with_sentiment, get_live_market_news

    ticker = extract_ticker_from_question(question)
    if ticker:
        articles, sentiment = get_company_news_with_sentiment(ticker, limit=5)
        return {
            "domain": "news", "ticker": ticker,
            "headlines": [a["headline"] for a in articles],
            "sentiment_label": sentiment.sentiment_label, "market_bias": sentiment.market_bias,
        }

    articles = get_live_market_news(limit=8)
    return {"domain": "news", "ticker": None, "headlines": [a["headline"] for a in articles]}


def _build_sentiment_context(question: str) -> dict[str, Any]:
    from market_intelligence.market_sentiment import compute_market_sentiment
    from market_intelligence.news_service import get_company_news_with_sentiment

    ticker = extract_ticker_from_question(question)
    if ticker:
        _, sentiment = get_company_news_with_sentiment(ticker, limit=10)
        return {
            "domain": "sentiment", "ticker": ticker,
            "sentiment_label": sentiment.sentiment_label, "market_bias": sentiment.market_bias,
            "confidence": sentiment.confidence, "article_count": sentiment.article_count,
        }

    report = compute_market_sentiment()
    return {
        "domain": "sentiment", "ticker": None, "overall_mood": report.overall_mood,
        "advancing": report.advancing_count, "declining": report.declining_count,
        "breadth_pct": report.breadth_pct,
    }


def _build_ipo_context() -> dict[str, Any]:
    from market_intelligence.ipo_service import ipo_service

    ipo_service.refresh_all_statuses()
    open_ipos = ipo_service.get_by_status("OPEN", page_size=10)["items"]
    upcoming_ipos = ipo_service.get_by_status("UPCOMING", page_size=10)["items"]

    return {
        "domain": "ipo",
        "open": [{"company": i.company_name, "subscription": float(i.subscription_times) if i.subscription_times else None} for i in open_ipos],
        "upcoming": [{"company": i.company_name, "open_date": i.open_date.isoformat() if i.open_date else None} for i in upcoming_ipos],
    }


def _build_notifications_context(user_id: int) -> dict[str, Any]:
    from market_intelligence.notification_service import get_notifications, get_unread_count

    unread_count = get_unread_count(user_id)
    recent = get_notifications(user_id, unread_only=True, page_size=5)["items"]

    return {
        "domain": "notifications", "unread_count": unread_count,
        "recent": [{"title": n.title, "message": n.message} for n in recent],
    }


def _build_company_context(question: str) -> dict[str, Any]:
    from stock_search.company_profile import get_company_info

    ticker = extract_ticker_from_question(question)
    if not ticker:
        return {"domain": "company", "error": "Could not identify which company you're asking about."}

    info = get_company_info(ticker)
    if info is None:
        return {"domain": "company", "ticker": ticker, "error": "Company data unavailable."}

    return {
        "domain": "company", "ticker": ticker,
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"), "industry": info.get("industry"),
        "market_cap": info.get("marketCap"), "pe_ratio": info.get("trailingPE"),
        "eps": info.get("trailingEps"), "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "summary": (info.get("longBusinessSummary") or "")[:400],
    }


def _build_technical_context(question: str) -> dict[str, Any]:
    from analytics.indicator_service import get_ohlcv, has_sufficient_data
    from analytics.signal_generator import generate_signals, get_overall_recommendation
    from analytics.technical_indicators import compute_all_indicators
    from analytics.trend_analysis import analyze_trend

    ticker = extract_ticker_from_question(question)
    if not ticker:
        return {"domain": "technical", "error": "Could not identify which company you're asking about."}

    df = get_ohlcv(ticker, "6 Month")
    if not has_sufficient_data(df, minimum_bars=30):
        return {"domain": "technical", "ticker": ticker, "error": "Not enough price history available."}

    indicators = compute_all_indicators(df)
    trend = analyze_trend(df)
    signals = generate_signals(df)
    overall, buy_count, sell_count, neutral_count = get_overall_recommendation(signals)

    return {
        "domain": "technical", "ticker": ticker, "indicators": indicators, "trend": trend,
        "signals": signals, "overall_signal": overall,
        "buy_count": buy_count, "sell_count": sell_count, "neutral_count": neutral_count,
    }


def _build_prediction_context(user_id: int, question: str) -> dict[str, Any]:
    from machine_learning.prediction_history import get_ticker_prediction_history

    ticker = extract_ticker_from_question(question)
    if not ticker:
        return {"domain": "prediction", "error": "Could not identify which company you're asking about."}

    history = get_ticker_prediction_history(user_id, ticker, limit=3)
    if not history:
        return {
            "domain": "prediction", "ticker": ticker,
            "note": "No cached ML prediction found. Generate one from the ML Prediction page first.",
        }

    return {
        "domain": "prediction", "ticker": ticker,
        "predictions": [
            {
                "model": p.model_name, "horizon_days": p.prediction_horizon_days,
                "predicted_price": float(p.predicted_price),
                "confidence": float(p.confidence_score) if p.confidence_score is not None else None,
                "created_at": p.created_at.isoformat(),
            }
            for p in history
        ],
    }


def _build_recommendation_context(user_id: int, question: str) -> dict[str, Any]:
    from dashboard.market_data_service import fetch_quote
    from portfolio.recommendation_engine import generate_holding_recommendation

    ticker = extract_ticker_from_question(question)
    if not ticker:
        return {"domain": "recommendation", "error": "Could not identify which company you're asking about."}

    quote = fetch_quote(ticker)
    if quote is None:
        return {"domain": "recommendation", "ticker": ticker, "error": "Live price data unavailable."}

    rec = generate_holding_recommendation(user_id, ticker, quote["price"])
    return {
        "domain": "recommendation", "ticker": ticker,
        "overall_recommendation": rec.overall_recommendation, "reasoning": rec.reasoning,
        "technical_signal": rec.technical_signal, "ml_prediction_change_pct": rec.ml_prediction_change_pct,
        "sentiment_bias": rec.sentiment_bias,
    }
