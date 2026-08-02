"""
portfolio/portfolio_dashboard.py

Purpose: The main entry point for Portfolio Management & Investment
Analytics. Ties together every other file in this package -- holdings
CRUD, buy/sell transactions, performance metrics, allocation, sector
exposure, risk/health scores, dividend estimates, rebalancing
suggestions, and cross-module recommendations -- into one tabbed page,
following the exact same structure as `dashboard.dashboard.py`,
`analytics.technical_analysis.py`, and `market_intelligence.news_dashboard.py`.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException, ValidationError
from dashboard.chart_helpers import CHART_CONFIG
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from database.audit_service import audit_service
from helper import format_currency, format_percentage
from logging_config import logger

from portfolio.allocation_analysis import compute_asset_allocation
from portfolio.charts import (
    build_allocation_pie_chart,
    build_daily_performance_chart,
    build_portfolio_growth_chart,
    build_risk_gauge,
    build_sector_exposure_chart,
)
from portfolio.dividend_tracker import estimate_portfolio_dividends
from portfolio.portfolio_calculator import compute_portfolio_overview, rank_holdings_by_performance
from portfolio.portfolio_optimizer import generate_rebalancing_suggestions
from portfolio.portfolio_service import (
    get_live_quotes_for_holdings,
    get_portfolio_summary_live,
    get_top_winner_and_loser,
    get_user_holdings,
)
from portfolio.recommendation_engine import generate_portfolio_recommendations
from portfolio.risk_analysis import compute_risk_report
from portfolio.sector_analysis import compute_sector_allocation
from portfolio.transaction_service import buy_stock, sell_stock, transaction_history
from stock_search.search_service import resolve_ticker, validate_ticker_exists

_RECOMMENDATION_ICON = {"BUY MORE": "🟢", "HOLD": "🟡", "CONSIDER SELLING": "🔴"}


# ==========================================================
# Overview tab
# ==========================================================
def _render_overview_tab(user_id: int) -> None:
    overview = compute_portfolio_overview(user_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Investment", format_currency(overview.total_investment, "₹"))
    with col2:
        st.metric("Current Value", format_currency(overview.current_value, "₹"))
    with col3:
        st.metric(
            "Total P&L",
            format_currency(overview.total_profit_loss, "₹"),
            delta=format_percentage(overview.total_profit_loss_pct),
        )
    with col4:
        st.metric(
            "Today's Gain/Loss",
            format_currency(overview.todays_gain_loss, "₹"),
            delta=format_percentage(overview.todays_gain_loss_pct),
        )

    render_divider()

    top_winner, top_loser = get_top_winner_and_loser(user_id)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🏆 Top Winner**")
        if top_winner:
            st.write(f"{top_winner['ticker_symbol']} — {format_percentage(top_winner['profit_loss_pct'])}")
        else:
            st.caption("No holdings yet.")
    with col2:
        st.markdown("**📉 Top Loser**")
        if top_loser:
            st.write(f"{top_loser['ticker_symbol']} — {format_percentage(top_loser['profit_loss_pct'])}")
        else:
            st.caption("No holdings yet.")

    render_divider()
    render_section_header("Holdings", icon="📦")
    summary = get_portfolio_summary_live(user_id)
    if not summary["holdings"]:
        st.info("You have no holdings yet. Use the form below to record your first trade.")
    else:
        ranked = rank_holdings_by_performance(summary["holdings"])
        rows = [
            {
                "Ticker": h["ticker_symbol"],
                "Qty": h["quantity"],
                "Avg. Buy Price": format_currency(h["average_buy_price"], "₹"),
                "Current Price": format_currency(h["current_price"], "₹"),
                "Current Value": format_currency(h["current_value"], "₹"),
                "P&L": format_currency(h["profit_loss"], "₹"),
                "P&L %": format_percentage(h["profit_loss_pct"]),
            }
            for h in ranked
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    render_divider()
    _render_transaction_form(user_id)


def _render_transaction_form(user_id: int) -> None:
    render_section_header("Record a Transaction", icon="💱")

    with st.form("portfolio_transaction_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            query = st.text_input("Company / Ticker", placeholder="e.g. TCS, RELIANCE.NS")
        with col2:
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
        with col3:
            price = st.number_input("Price per Share (₹)", min_value=0.0, step=0.5)

        notes = st.text_input("Notes (optional)")
        col_buy, col_sell = st.columns(2)
        with col_buy:
            buy_submitted = st.form_submit_button("🟢 Buy", use_container_width=True)
        with col_sell:
            sell_submitted = st.form_submit_button("🔴 Sell", use_container_width=True)

    if not (buy_submitted or sell_submitted):
        return

    try:
        ticker = resolve_ticker(query)
        if not validate_ticker_exists(ticker):
            st.error(f"'{query}' could not be resolved to a valid ticker.")
            return
        if quantity <= 0 or price <= 0:
            st.warning("Quantity and price must both be greater than zero.")
            return

        if buy_submitted:
            buy_stock(user_id, ticker, quantity, price, notes or None)
            st.success(f"Bought {quantity} shares of {ticker} at {format_currency(price, '₹')}.")
        else:
            sell_stock(user_id, ticker, quantity, price, notes or None)
            st.success(f"Sold {quantity} shares of {ticker} at {format_currency(price, '₹')}.")
        st.rerun()
    except ValidationError as exc:
        st.warning(exc.message)
    except FinSightBaseException as exc:
        logger.error(f"Transaction failed: {exc}")
        st.error(exc.message)


# ==========================================================
# Performance tab
# ==========================================================
def _render_performance_tab(user_id: int) -> None:
    from portfolio.performance_metrics import compute_performance_metrics

    render_section_header("Performance Metrics", icon="📈")
    metrics = compute_performance_metrics(user_id)

    if metrics.expected_return_pct is None:
        st.info("Not enough historical data yet to compute performance metrics. Check back after your holdings have more price history.")
    else:
        cols = st.columns(5)
        cols[0].metric("Expected Return", format_percentage(metrics.expected_return_pct))
        cols[1].metric("Volatility", format_percentage(metrics.volatility_pct))
        cols[2].metric("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio is not None else "N/A")
        cols[3].metric("Beta", f"{metrics.beta:.2f}" if metrics.beta is not None else "N/A")
        cols[4].metric("Max Drawdown", format_percentage(metrics.max_drawdown_pct))

    render_divider()
    render_section_header("Portfolio Growth", icon="📊")
    transactions = transaction_history(user_id, page_size=500)["items"]
    transaction_dicts = [
        {"transaction_date": t.transaction_date, "transaction_type": t.transaction_type, "total_amount": float(t.total_amount)}
        for t in transactions
    ]
    st.plotly_chart(build_portfolio_growth_chart(transaction_dicts), use_container_width=True, config=CHART_CONFIG, key="portfolio_growth_chart")

    render_divider()
    render_section_header("Today's Performance by Holding", icon="📅")
    holdings = get_user_holdings(user_id, page_size=1000)["items"]
    quotes = get_live_quotes_for_holdings(holdings)
    holding_dicts = [{"ticker_symbol": h.ticker_symbol, "quantity": float(h.quantity)} for h in holdings]
    st.plotly_chart(build_daily_performance_chart(holding_dicts, quotes), use_container_width=True, config=CHART_CONFIG, key="daily_performance_chart")


# ==========================================================
# Allocation tab
# ==========================================================
def _render_allocation_tab(user_id: int) -> None:
    render_section_header("Asset Allocation", icon="🥧")
    allocation = compute_asset_allocation(user_id)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(build_allocation_pie_chart(allocation.weights), use_container_width=True, config=CHART_CONFIG, key="allocation_pie_chart")
    with col2:
        st.metric("Diversification Score", f"{allocation.diversification_score:.0f}/100")
        st.caption(allocation.concentration_label)
        if allocation.largest_holding_ticker:
            st.metric("Largest Holding", allocation.largest_holding_ticker, delta=format_percentage(allocation.largest_holding_pct))

    render_divider()
    render_section_header("Sector Exposure", icon="🏭")
    sector = compute_sector_allocation(user_id)
    st.plotly_chart(build_sector_exposure_chart(sector.sector_weights), use_container_width=True, config=CHART_CONFIG, key="sector_exposure_chart")

    render_divider()
    render_section_header("Rebalancing Suggestions", subtitle="Compared to an equal-weight target", icon="⚖️")
    suggestions = generate_rebalancing_suggestions(user_id)
    if not suggestions:
        st.info("No holdings to rebalance yet.")
    else:
        rows = [
            {
                "Ticker": s.ticker, "Current %": s.current_weight_pct, "Target %": s.target_weight_pct,
                "Drift %": s.drift_pct, "Action": s.action, "Suggested Value Change": format_currency(s.suggested_value_change, "₹"),
            }
            for s in suggestions
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


# ==========================================================
# Risk tab
# ==========================================================
def _render_risk_tab(user_id: int) -> None:
    render_section_header("Risk & Health", icon="🛡️")
    report = compute_risk_report(user_id)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(build_risk_gauge(report.risk_score, report.risk_label), use_container_width=True, config=CHART_CONFIG, key="risk_gauge")
    with col2:
        st.metric("Portfolio Health Score", f"{report.health_score:.0f}/100", delta=report.health_label)
        st.caption(f"Volatility contribution: {report.volatility_component:.1f}" if report.volatility_component is not None else "Volatility: N/A")
        st.caption(f"Concentration contribution: {report.concentration_component:.1f}")
        st.caption(f"Sector concentration contribution: {report.sector_concentration_component:.1f}")


# ==========================================================
# Dividends tab
# ==========================================================
def _render_dividends_tab(user_id: int) -> None:
    render_section_header("Dividend Tracker", subtitle="Estimated from current holdings and trailing dividend yield", icon="💰")
    estimate = estimate_portfolio_dividends(user_id)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Est. Annual Dividend Income", format_currency(estimate.total_estimated_annual_income, "₹"))
    with col2:
        st.metric("Portfolio Average Yield", format_percentage(estimate.portfolio_average_yield_pct))

    if estimate.holdings:
        rows = [
            {"Ticker": h["ticker"], "Dividend Yield": format_percentage(h["yield_pct"]), "Est. Annual Income": format_currency(h["estimated_annual_income"], "₹")}
            for h in estimate.holdings
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No holdings yet.")


# ==========================================================
# Recommendations tab
# ==========================================================
def _render_recommendations_tab(user_id: int) -> None:
    render_section_header("Recommendations", subtitle="Combining Technical Analysis, ML Predictions, and Market Sentiment", icon="🧭")
    summary = get_portfolio_summary_live(user_id)
    if not summary["holdings"]:
        st.info("No holdings yet.")
        return

    with st.spinner("Analyzing holdings across Technical Analysis, ML predictions, and news sentiment..."):
        recommendations = generate_portfolio_recommendations(user_id, summary["holdings"])

    for rec in recommendations:
        icon = _RECOMMENDATION_ICON.get(rec.overall_recommendation, "⚪")
        with st.expander(f"{icon} {rec.ticker} — {rec.overall_recommendation}"):
            for line in rec.reasoning:
                st.write(f"• {line}")


# ==========================================================
# Main entry point
# ==========================================================
@login_required
def render() -> None:
    """Render the full Portfolio Management & Investment Analytics page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("💼 Portfolio Management")
        st.caption("Track holdings, analyze performance and risk, and get cross-module recommendations.")
        render_divider()

        audit_service.log_action(action="PORTFOLIO_VIEW", user_id=user_id)

        tabs = st.tabs(["Overview", "Performance", "Allocation", "Risk", "Dividends", "Recommendations"])
        with tabs[0]:
            _render_overview_tab(user_id)
        with tabs[1]:
            _render_performance_tab(user_id)
        with tabs[2]:
            _render_allocation_tab(user_id)
        with tabs[3]:
            _render_risk_tab(user_id)
        with tabs[4]:
            _render_dividends_tab(user_id)
        with tabs[5]:
            _render_recommendations_tab(user_id)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in portfolio dashboard: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in portfolio dashboard: {exc}")
        st.error("An unexpected error occurred while loading your portfolio. Please try again.")
