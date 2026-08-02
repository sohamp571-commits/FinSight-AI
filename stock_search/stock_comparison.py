"""
stock_search/stock_comparison.py

Purpose: Lets the user compare up to 5 companies side by side across
Price, Market Cap, P/E, EPS, Dividend, Revenue, Net Profit, ROE, and
ROA -- as both a table and a grouped Plotly bar chart. Reuses
`company_profile.get_company_info()` and `income_statement.get_income_statement()`
so no new yfinance access pattern is introduced.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, apply_dark_theme
from dashboard.dashboard_layout import render_section_header
from helper import format_currency
from logging_config import logger
from stock_search.company_profile import get_company_info
from stock_search.income_statement import get_income_statement
from stock_search.search_service import resolve_ticker, validate_ticker_exists
from utils import safe_divide

MAX_COMPARISON_TICKERS = 5


def _latest(df: pd.DataFrame | None, row_name: str) -> float | None:
    if df is None or row_name not in df.index:
        return None
    series = df.loc[row_name].dropna()
    return float(series.iloc[0]) if not series.empty else None


def _build_comparison_row(ticker: str) -> dict[str, Any] | None:
    """Fetch and assemble one company's comparison metrics."""
    info = get_company_info(ticker)
    if info is None:
        return None

    income_stmt = get_income_statement(ticker)
    net_income = _latest(income_stmt, "Net Income")
    total_revenue = _latest(income_stmt, "Total Revenue")

    return {
        "Ticker": ticker,
        "Company": info.get("longName") or info.get("shortName") or ticker,
        "Price": info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
        "Market Cap": info.get("marketCap") or 0,
        "P/E": info.get("trailingPE"),
        "EPS": info.get("trailingEps"),
        "Dividend Yield %": (info.get("dividendYield") or 0) * 100,
        "Revenue": total_revenue or 0,
        "Net Profit": net_income or 0,
        "ROE %": safe_divide(net_income, info.get("bookValue") or None, default=0.0) * 100 if net_income else 0.0,
    }


def render_stock_comparison() -> None:
    """Render the Stock Comparison tab: multi-select input, comparison table, and bar charts."""
    render_section_header("Stock Comparison", subtitle="Compare up to 5 companies side by side", icon="⚔️")

    raw_input = st.text_input(
        "Enter tickers or company names, separated by commas",
        placeholder="e.g. RELIANCE, TCS, INFY, HDFCBANK",
        key="comparison_input",
    )
    if not raw_input.strip():
        st.caption("Enter 2-5 companies above to compare them.")
        return

    queries = [q.strip() for q in raw_input.split(",") if q.strip()][:MAX_COMPARISON_TICKERS]
    if len(queries) > MAX_COMPARISON_TICKERS:
        st.warning(f"Only the first {MAX_COMPARISON_TICKERS} companies will be compared.")

    rows: list[dict[str, Any]] = []
    with st.spinner("Fetching comparison data..."):
        for query in queries:
            ticker = resolve_ticker(query)
            if not validate_ticker_exists(ticker):
                st.warning(f"'{query}' could not be resolved to a valid ticker and was skipped.")
                continue
            row = _build_comparison_row(ticker)
            if row is not None:
                rows.append(row)
            else:
                logger.warning(f"Comparison data unavailable for {ticker}.")

    if not rows:
        st.info("No valid companies to compare yet.")
        return

    df = pd.DataFrame(rows).set_index("Ticker")
    display_df = df.copy()
    display_df["Price"] = display_df["Price"].map(lambda v: format_currency(v, "₹"))
    display_df["Market Cap"] = display_df["Market Cap"].map(lambda v: format_currency(v, "₹"))
    display_df["Revenue"] = display_df["Revenue"].map(lambda v: format_currency(v, "₹"))
    display_df["Net Profit"] = display_df["Net Profit"].map(lambda v: format_currency(v, "₹"))
    st.dataframe(display_df, use_container_width=True)

    metric_to_chart = st.selectbox("Chart metric", ["P/E", "EPS", "ROE %", "Revenue", "Net Profit"])
    fig = go.Figure(
        go.Bar(
            x=df["Company"],
            y=df[metric_to_chart].fillna(0),
            marker_color=COLOR_ACCENT,
            text=df[metric_to_chart].round(2),
            textposition="outside",
        )
    )
    fig.update_layout(title=f"{metric_to_chart} Comparison")
    fig = apply_dark_theme(fig, height=380)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="comparison_chart")
