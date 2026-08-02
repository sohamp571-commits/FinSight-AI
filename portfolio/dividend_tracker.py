"""
portfolio/dividend_tracker.py

Purpose: Estimates dividend income for the portfolio. No table tracks
actual dividend receipt events (the Phase 9 brief only pre-approved
`portfolio`/`portfolio_transactions`, both of which already exist and
cover buy/sell only) -- rather than inventing a new table for this,
dividend income is *estimated* from each holding's current value and
trailing dividend yield, reusing `stock_search.company_profile.get_company_info()`
(the same cached yfinance `.info` call Stock Search already makes) instead
of a new data source.
"""

from dataclasses import dataclass

from portfolio.portfolio_service import get_portfolio_summary_live
from stock_search.company_profile import get_company_info


@dataclass
class DividendEstimate:
    """Estimated annual dividend income for the whole portfolio."""

    holdings: list[dict]  # [{"ticker": str, "yield_pct": float, "estimated_annual_income": float}, ...]
    total_estimated_annual_income: float
    portfolio_average_yield_pct: float


def estimate_portfolio_dividends(user_id: int) -> DividendEstimate:
    """Estimate annual dividend income across every holding based on current value x dividend yield."""
    summary = get_portfolio_summary_live(user_id)
    holdings = summary["holdings"]

    if not holdings:
        return DividendEstimate(holdings=[], total_estimated_annual_income=0.0, portfolio_average_yield_pct=0.0)

    rows = []
    total_income = 0.0
    total_value = 0.0

    for holding in holdings:
        ticker = holding["ticker_symbol"]
        current_value = holding["current_value"]
        info = get_company_info(ticker)
        dividend_yield_pct = round((info.get("dividendYield") or 0) * 100, 2) if info else 0.0
        estimated_income = round(current_value * (dividend_yield_pct / 100), 2)

        rows.append({"ticker": ticker, "yield_pct": dividend_yield_pct, "estimated_annual_income": estimated_income})
        total_income += estimated_income
        total_value += current_value

    average_yield = round((total_income / total_value) * 100, 2) if total_value else 0.0

    return DividendEstimate(
        holdings=sorted(rows, key=lambda r: r["estimated_annual_income"], reverse=True),
        total_estimated_annual_income=round(total_income, 2),
        portfolio_average_yield_pct=average_yield,
    )
