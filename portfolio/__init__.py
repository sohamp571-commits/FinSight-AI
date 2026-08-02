"""
portfolio package

Phase 9 — Portfolio Management & Investment Analytics for FinSight AI.

No new database tables were needed: the existing `portfolio` and
`transactions` tables (Phase 1 schema, Phase 3
`database.portfolio_service` / `database.transaction_service`) already
cover holdings and buy/sell transactions completely.

Sub-modules:
    portfolio_service.py       - facade over database.portfolio_service + live-quote reads
    transaction_service.py      - facade over database.transaction_service + audit logging
    portfolio_calculator.py      - headline overview numbers (investment/value/P&L)
    performance_metrics.py        - Expected Return, Volatility, Sharpe, Beta, Max Drawdown
    allocation_analysis.py         - asset allocation + diversification score (HHI)
    sector_analysis.py              - sector exposure (reuses market_intelligence.SECTOR_MAP)
    risk_analysis.py                 - composite risk score + portfolio health score
    dividend_tracker.py               - estimated dividend income (reuses stock_search company info)
    portfolio_optimizer.py             - rebalancing suggestions vs. equal-weight target
    recommendation_engine.py            - per-holding recommendations (Technical + ML + Sentiment)
    charts.py                            - every Portfolio-specific Plotly chart
    portfolio_dashboard.py                - main controller (entry point: portfolio_dashboard.render)
"""

from portfolio.portfolio_dashboard import render

__all__ = ["render"]
