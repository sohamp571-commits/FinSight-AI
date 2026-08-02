"""
ai_assistant/recommendation_engine.py

Purpose: Handles the "give me recommendations across my whole
portfolio" style of question -- distinct from `context_builder.py`'s
single-ticker recommendation path (used for "should I buy more X").
Both ultimately call the exact same underlying function,
`portfolio.recommendation_engine.generate_holding_recommendation()`
(Phase 9) -- nothing here recomputes technical signals, ML
predictions, or sentiment.
"""

from portfolio.portfolio_service import get_portfolio_summary_live
from portfolio.recommendation_engine import HoldingRecommendation, generate_portfolio_recommendations


def get_portfolio_wide_recommendations(user_id: int) -> list[HoldingRecommendation]:
    """Reuse portfolio.recommendation_engine across every current holding."""
    summary = get_portfolio_summary_live(user_id)
    if not summary["holdings"]:
        return []
    return generate_portfolio_recommendations(user_id, summary["holdings"])


def summarize_portfolio_recommendations(recommendations: list[HoldingRecommendation]) -> str:
    """Format a list of per-holding recommendations into one conversational summary."""
    if not recommendations:
        return "You have no holdings yet, so there's nothing to recommend on."

    buy_more = [r.ticker for r in recommendations if r.overall_recommendation == "BUY MORE"]
    hold = [r.ticker for r in recommendations if r.overall_recommendation == "HOLD"]
    consider_selling = [r.ticker for r in recommendations if r.overall_recommendation == "CONSIDER SELLING"]

    lines = [f"Here's a quick read across your {len(recommendations)} holding(s):"]
    if buy_more:
        lines.append(f"🟢 **Buy More:** {', '.join(buy_more)}")
    if hold:
        lines.append(f"🟡 **Hold:** {', '.join(hold)}")
    if consider_selling:
        lines.append(f"🔴 **Consider Selling:** {', '.join(consider_selling)}")

    return "\n\n".join(lines)
