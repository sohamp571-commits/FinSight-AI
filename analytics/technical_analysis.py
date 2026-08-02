"""
analytics/technical_analysis.py

Purpose: The main entry point for the Technical Analysis module. Lets
the user search for a ticker (reusing stock_search's resolution logic),
pick a timeframe, and explore price via candlestick/line/area charts
with overlays, every individual indicator panel, support/resistance,
volume analysis, and the consolidated Buy/Sell/Neutral signal summary.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from database.audit_service import audit_service
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from logging_config import logger

from analytics.adx import render_adx_panel
from analytics.area_chart import render_area_chart_panel
from analytics.atr import render_atr_panel
from analytics.bollinger_bands import render_bollinger_panel
from analytics.candlestick_chart import render_candlestick_panel
from analytics.indicator_service import DEFAULT_TIMEFRAME, TIMEFRAME_OPTIONS, get_ohlcv, has_sufficient_data
from analytics.line_chart import render_line_chart_panel
from analytics.macd import render_macd_panel
from analytics.moving_average import render_moving_average_panel
from analytics.rsi import render_rsi_panel
from analytics.signal_generator import render_signal_summary
from analytics.stochastic import render_stochastic_panel
from analytics.support_resistance import render_support_resistance_panel
from analytics.technical_indicators import render_all_indicators_table
from analytics.trend_analysis import render_trend_summary
from analytics.volume_chart import render_volume_panel
from stock_search.search_service import resolve_ticker, validate_ticker_exists


def _render_ticker_and_timeframe_controls() -> tuple[str | None, str]:
    """Render the ticker search box and timeframe selector, returning (resolved_ticker, timeframe_label)."""
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "🔍 Company name or ticker symbol",
            placeholder="e.g. Reliance Industries, TCS, INFY.NS, AAPL",
            key="ta_search_query",
        )
    with col2:
        timeframe_label = st.selectbox("Timeframe", list(TIMEFRAME_OPTIONS.keys()), index=list(TIMEFRAME_OPTIONS.keys()).index(DEFAULT_TIMEFRAME))

    if not query.strip():
        return None, timeframe_label

    ticker = resolve_ticker(query)
    if not validate_ticker_exists(ticker):
        st.error(f"'{query}' could not be resolved to a valid, actively-traded ticker.")
        return None, timeframe_label

    return ticker, timeframe_label


@login_required
def render() -> None:
    """Render the full Technical Analysis page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("📉 Technical Analysis")
        st.caption("Professional charting and indicators, powered by live market data.")
        render_divider()

        ticker, timeframe_label = _render_ticker_and_timeframe_controls()

        if ticker is None:
            st.info("Search for a company above to begin technical analysis.")
            return

        with st.spinner(f"Loading {timeframe_label.lower()} price data for {ticker}..."):
            df = get_ohlcv(ticker, timeframe_label)

        if not has_sufficient_data(df, minimum_bars=15):
            st.warning(
                f"Not enough price history is available for {ticker} on the '{timeframe_label}' "
                f"timeframe to compute reliable indicators. Try a longer timeframe."
            )
            return

        audit_service.log_action(
            action="TECHNICAL_ANALYSIS_VIEW", user_id=user_id, entity_type="ticker", details=ticker
        )

        chart_tab, indicators_tab, signals_tab = st.tabs(["📈 Charts", "📊 Indicators", "🎯 Signals"])

        with chart_tab:
            render_section_header("Price Chart", subtitle=f"{ticker} — {timeframe_label}", icon="🕯️")
            chart_type = st.radio("Chart Type", ["Candlestick", "Line", "Area"], horizontal=True, key="ta_chart_type")

            if chart_type == "Candlestick":
                render_candlestick_panel(df, ticker)
            elif chart_type == "Line":
                render_line_chart_panel(df, ticker)
            else:
                render_area_chart_panel(df, ticker)

            render_divider()
            render_volume_panel(df)

        with indicators_tab:
            render_trend_summary(df)
            render_divider()

            sub_tabs = st.tabs(
                ["Moving Averages", "RSI", "MACD", "Bollinger Bands", "Stochastic", "ATR", "ADX", "Support/Resistance", "All Indicators"]
            )
            with sub_tabs[0]:
                render_moving_average_panel(df)
            with sub_tabs[1]:
                render_rsi_panel(df)
            with sub_tabs[2]:
                render_macd_panel(df)
            with sub_tabs[3]:
                render_bollinger_panel(df)
            with sub_tabs[4]:
                render_stochastic_panel(df)
            with sub_tabs[5]:
                render_atr_panel(df)
            with sub_tabs[6]:
                render_adx_panel(df)
            with sub_tabs[7]:
                render_support_resistance_panel(df)
            with sub_tabs[8]:
                render_all_indicators_table(df)

        with signals_tab:
            render_signal_summary(df)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in technical analysis: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in technical analysis: {exc}")
        st.error("An unexpected error occurred while loading technical analysis. Please try again.")
