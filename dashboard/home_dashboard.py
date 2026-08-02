"""
dashboard/home_dashboard.py

Purpose: Phase 12's personalized home/landing page -- replaces
app.py's `_render_dashboard_placeholder()`. Shows Portfolio Value,
Today's Profit, Market Status, Watchlist Count, AI Confidence, an
interactive market chart, latest news, trending stocks, recent
activity, and quick actions.

Every number here is a direct pass-through from an existing service
(Phase 3/4/7/8/9) -- this file contains no financial calculations of
its own, matching the project's established "no duplicate
calculations" convention from Phases 9-11.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_full_name, get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.chart_helpers import CHART_CONFIG, build_price_line_chart
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header, responsive_columns
from dashboard.market_data_service import MARKET_INDICES, fetch_price_history, get_market_status
from database.audit_service import audit_service
from database.watchlist_service import watchlist_service
from helper import format_currency, format_datetime, format_percentage
from logging_config import logger

_QUICK_ACTIONS = [
    ("🔍 Search a Stock", "stock_search"),
    ("💼 View Portfolio", "portfolio"),
    ("📉 Technical Analysis", "technical_analysis"),
    ("🤖 Ask AI Assistant", "ai_assistant"),
]


def _render_kpi_row(user_id: int) -> None:
    """Render the headline KPI row: Portfolio Value, Today's Profit, Market Status, Watchlist Count, AI Confidence."""
    from portfolio.portfolio_calculator import compute_portfolio_overview

    try:
        overview = compute_portfolio_overview(user_id)
        portfolio_value = format_currency(overview.current_value, "₹")
        todays_profit = format_currency(overview.todays_gain_loss, "₹")
        todays_profit_pct = format_percentage(overview.todays_gain_loss_pct)
    except FinSightBaseException as exc:
        logger.warning(f"Could not load portfolio KPIs for home dashboard: {exc}")
        portfolio_value, todays_profit, todays_profit_pct = "N/A", "N/A", None

    market_status = get_market_status()
    watchlist_count = watchlist_service.count(filters={"user_id": user_id})
    ai_confidence = _compute_average_ai_confidence(user_id)

    columns = responsive_columns(5, max_cols=5)
    with columns[0]:
        st.metric("Portfolio Value", portfolio_value)
    with columns[1]:
        st.metric("Today's Profit", todays_profit, delta=todays_profit_pct)
    with columns[2]:
        st.metric("Market Status", market_status["label"])
    with columns[3]:
        st.metric("Watchlist", f"{watchlist_count} ticker(s)")
    with columns[4]:
        st.metric("AI Confidence", ai_confidence)


def _compute_average_ai_confidence(user_id: int) -> str:
    """Average confidence_score across the user's cached ML predictions (reused from Phase 7)."""
    from machine_learning.prediction_history import get_all_prediction_history

    history = get_all_prediction_history(user_id, limit=25)
    scored = [float(p.confidence_score) for p in history if p.confidence_score is not None]
    if not scored:
        return "No predictions yet"
    return format_percentage(sum(scored) / len(scored))


def _render_market_chart() -> None:
    """Render an interactive NIFTY 50 chart as the home page's market pulse (reused chart_helpers/market_data_service)."""
    render_section_header("Market Pulse — NIFTY 50", icon="📊")
    history = fetch_price_history(MARKET_INDICES["NIFTY 50"], period="3mo", interval="1d")
    if history is None or history.empty:
        st.info("Market chart is temporarily unavailable.")
        return
    fig = build_price_line_chart(history, title="NIFTY 50 — Last 3 Months")
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="home_market_chart")


def _render_gainers_losers() -> None:
    """Render Top Gainers and Top Losers side by side (reused directly from Phase 4, dashboard/top_gainers.py + top_losers.py)."""
    from dashboard.top_gainers import render_top_gainers
    from dashboard.top_losers import render_top_losers

    col1, col2 = st.columns(2)
    with col1:
        render_top_gainers(limit=5)
    with col2:
        render_top_losers(limit=5)


def _render_news_and_trending() -> None:
    """Render Latest News and Trending Stocks side by side (reused from market_intelligence, Phase 8)."""
    from market_intelligence.news_service import get_live_market_news, get_trending_stocks

    col1, col2 = st.columns(2)
    with col1:
        render_section_header("Latest News", icon="📰")
        articles = get_live_market_news(limit=5)
        if not articles:
            st.caption("No recent news available.")
        for article in articles:
            st.markdown(f"• [{article['headline']}]({article['url']})")

    with col2:
        render_section_header("Trending Stocks", icon="🔥")
        with st.spinner("Analyzing trending stocks..."):
            trending = get_trending_stocks(top_n=5)
        if not trending:
            st.caption("No trending data available.")
        for ticker, count in trending:
            st.markdown(f"• **{ticker}** — {count} article(s)")


def _render_recent_activity(user_id: int) -> None:
    """Render the user's recent activity from the existing audit_logs table (Phase 3)."""
    render_section_header("Recent Activity", icon="🕓")
    logs = audit_service.get_logs_for_user(user_id, page_size=5)["items"]
    if not logs:
        st.caption("No recent activity yet.")
        return
    for entry in logs:
        st.markdown(f"• {entry.action.replace('_', ' ').title()} — {format_datetime(entry.created_at)}")


def _render_quick_actions() -> None:
    """Render quick-action buttons that jump straight to other modules."""
    render_section_header("Quick Actions", icon="⚡")
    columns = responsive_columns(len(_QUICK_ACTIONS), max_cols=4)
    for column, (label, nav_target) in zip(columns, _QUICK_ACTIONS):
        with column:
            if st.button(label, use_container_width=True, key=f"quick_action_{nav_target}"):
                st.session_state["nav_target"] = nav_target
                st.rerun()


@login_required
def render() -> None:
    """Render the full personalized home dashboard."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()
        full_name = get_current_full_name() or "there"

        st.title(f"Welcome back, {full_name} 👋")
        st.caption("Here's what's happening across your portfolio and the market today.")
        render_divider()

        _render_kpi_row(user_id)
        render_divider()

        _render_market_chart()
        render_divider()

        _render_gainers_losers()
        render_divider()

        _render_news_and_trending()
        render_divider()

        col1, col2 = st.columns([1, 1])
        with col1:
            _render_recent_activity(user_id)
        with col2:
            _render_quick_actions()

    except FinSightBaseException as exc:
        logger.error(f"Handled error in home dashboard: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in home dashboard: {exc}")
        st.error("An unexpected error occurred while loading your dashboard. Please try again.")
