"""
dashboard package

Phase 4 — Live Market Dashboard for FinSight AI.

Sub-modules:
    market_data_service.py  - yfinance access layer (caching, retry, market universe)
    chart_helpers.py         - reusable Plotly chart builders + shared dark theme
    dashboard_layout.py      - CSS injection, section headers, responsive columns
    dashboard_widgets.py     - KPI cards, movers table, status badge
    market_status.py         - market open/closed indicator
    market_indices.py        - indices + commodities/crypto/forex KPI grid
    market_overview.py       - Overview tab (status + indices + user snapshot)
    top_gainers.py / top_losers.py / most_active.py
                              - mover tables for the tracked universe
    market_heatmap.py        - Plotly treemap heatmap
    navigation.py             - in-page tab navigation
    sidebar.py                 - dashboard-specific sidebar controls
    dashboard.py               - main controller (entry point: dashboard.render)
"""

from dashboard.dashboard import render

__all__ = ["render"]
