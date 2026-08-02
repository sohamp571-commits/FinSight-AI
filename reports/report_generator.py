"""
reports/report_generator.py

Purpose: Gathers every fact the Portfolio Report needs into one
`ReportData` object. Every field is retrieved from an existing service
already built in Phases 3, 5, and 9-10 -- this module contains no
financial math of its own, only orchestration, matching the Phase 11
"no duplicate calculations, no duplicate database queries" requirement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ai_assistant.context_builder import build_context
from ai_assistant.intent_classifier import INTENT_PORTFOLIO, ClassifiedIntent
from ai_assistant.llm_client import generate_llm_response, is_llm_configured
from ai_assistant.prompt_builder import build_prompt
from ai_assistant.recommendation_engine import get_portfolio_wide_recommendations, summarize_portfolio_recommendations
from ai_assistant.rule_based_responder import generate_rule_based_response
from portfolio.allocation_analysis import compute_asset_allocation
from portfolio.dividend_tracker import estimate_portfolio_dividends
from portfolio.performance_metrics import compute_performance_metrics
from portfolio.portfolio_calculator import compute_portfolio_overview, rank_holdings_by_performance
from portfolio.portfolio_service import get_portfolio_summary_live, get_top_winner_and_loser
from portfolio.risk_analysis import compute_risk_report
from portfolio.sector_analysis import compute_sector_allocation
from portfolio.transaction_service import transaction_history


@dataclass
class ReportData:
    """Every fact and figure the Portfolio Report PDF needs, gathered from existing services."""

    generated_at: datetime
    username: str

    total_investment: float
    current_value: float
    total_profit_loss: float
    total_profit_loss_pct: float
    todays_gain_loss: float
    holdings_count: int

    holdings: list[dict[str, Any]]
    top_winner: dict[str, Any] | None
    top_loser: dict[str, Any] | None

    allocation_weights: dict[str, float]
    diversification_score: float
    concentration_label: str

    sector_weights: dict[str, float]

    risk_score: float
    risk_label: str
    health_score: float
    health_label: str

    expected_return_pct: float | None
    volatility_pct: float | None
    sharpe_ratio: float | None
    beta: float | None
    max_drawdown_pct: float | None

    dividend_total_estimated: float
    dividend_average_yield_pct: float
    dividend_holdings: list[dict[str, Any]]

    recommendation_summary: str
    ai_assistant_summary: str

    transactions: list[dict[str, Any]] = field(default_factory=list)


def _generate_ai_summary(user_id: int) -> str:
    """
    Generate the "AI Assistant Summary" section by reusing Phase 10's
    context_builder + LLM/rule-based response paths directly -- NOT
    `ai_assistant.ask()`, which would also write this synthetic
    question into the user's visible chat history as a side effect.
    """
    classified = ClassifiedIntent(intent=INTENT_PORTFOLIO, raw_question="Summarize my portfolio performance.")
    context = build_context(user_id, classified)

    if is_llm_configured():
        prompt = build_prompt(classified.raw_question, context, [])
        answer = generate_llm_response(prompt)
        if answer:
            return answer

    return generate_rule_based_response(context)


def generate_report_data(user_id: int, username: str) -> ReportData:
    """
    Build the full ReportData object for a user's Portfolio Report.
    Every value below is a direct pass-through from an existing
    service call -- see each service's own module for the underlying
    calculation.
    """
    overview = compute_portfolio_overview(user_id)
    summary = get_portfolio_summary_live(user_id)
    top_winner, top_loser = get_top_winner_and_loser(user_id)
    ranked_holdings = rank_holdings_by_performance(summary["holdings"])

    allocation = compute_asset_allocation(user_id)
    sector = compute_sector_allocation(user_id)
    risk = compute_risk_report(user_id)
    performance = compute_performance_metrics(user_id)
    dividends = estimate_portfolio_dividends(user_id)

    recommendations = get_portfolio_wide_recommendations(user_id)
    recommendation_summary = summarize_portfolio_recommendations(recommendations)

    ai_summary = _generate_ai_summary(user_id)

    transactions = transaction_history(user_id, page_size=500)["items"]
    transaction_dicts = [
        {
            "transaction_date": t.transaction_date,
            "transaction_type": t.transaction_type,
            "total_amount": float(t.total_amount),
        }
        for t in transactions
    ]

    return ReportData(
        generated_at=datetime.utcnow(),
        username=username,
        total_investment=overview.total_investment,
        current_value=overview.current_value,
        total_profit_loss=overview.total_profit_loss,
        total_profit_loss_pct=overview.total_profit_loss_pct,
        todays_gain_loss=overview.todays_gain_loss,
        holdings_count=overview.holdings_count,
        holdings=ranked_holdings,
        top_winner=top_winner,
        top_loser=top_loser,
        allocation_weights=allocation.weights,
        diversification_score=allocation.diversification_score,
        concentration_label=allocation.concentration_label,
        sector_weights=sector.sector_weights,
        risk_score=risk.risk_score,
        risk_label=risk.risk_label,
        health_score=risk.health_score,
        health_label=risk.health_label,
        expected_return_pct=performance.expected_return_pct,
        volatility_pct=performance.volatility_pct,
        sharpe_ratio=performance.sharpe_ratio,
        beta=performance.beta,
        max_drawdown_pct=performance.max_drawdown_pct,
        dividend_total_estimated=dividends.total_estimated_annual_income,
        dividend_average_yield_pct=dividends.portfolio_average_yield_pct,
        dividend_holdings=dividends.holdings,
        recommendation_summary=recommendation_summary,
        ai_assistant_summary=ai_summary,
        transactions=transaction_dicts,
    )
