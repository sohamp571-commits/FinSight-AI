"""
stock_search/valuation_metrics.py

Purpose: Renders valuation multiples that yfinance exposes directly on
the `.info` payload -- P/E, P/B, PEG, EV/EBITDA, Price/Sales, and
Dividend Yield -- as a KPI-style grid with a one-line plain-English
interpretation for each metric. Distinct from fundamental_analysis.py,
which computes ratios that require pulling the income statement/
balance sheet (ROE, ROA, margins, liquidity ratios).
"""

from typing import Any

import streamlit as st

from dashboard.dashboard_layout import render_section_header, responsive_columns
from helper import format_percentage
from stock_search.company_profile import get_company_info


def _interpret_pe(pe: float | None) -> str:
    if pe is None:
        return "N/A"
    if pe < 15:
        return "Potentially undervalued"
    if pe <= 25:
        return "Fairly valued"
    return "Premium valuation"


def _interpret_pb(pb: float | None) -> str:
    if pb is None:
        return "N/A"
    if pb < 1:
        return "Trading below book value"
    if pb <= 3:
        return "Reasonable"
    return "Rich valuation"


def render_valuation_metrics(ticker: str) -> None:
    """Render the Valuation Metrics section."""
    info: dict[str, Any] | None = get_company_info(ticker)
    if info is None:
        st.info(f"Valuation metrics are not available for {ticker}.")
        return

    render_section_header("Valuation Metrics", icon="⚖️")

    pe_ratio = info.get("trailingPE")
    pb_ratio = info.get("priceToBook")
    peg_ratio = info.get("pegRatio") or info.get("trailingPegRatio")
    ev_ebitda = info.get("enterpriseToEbitda")
    price_to_sales = info.get("priceToSalesTrailing12Months")
    dividend_yield = info.get("dividendYield")

    metrics: list[tuple[str, str, str]] = [
        ("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio is not None else "N/A", _interpret_pe(pe_ratio)),
        ("P/B Ratio", f"{pb_ratio:.2f}" if pb_ratio is not None else "N/A", _interpret_pb(pb_ratio)),
        ("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio is not None else "N/A", "Growth-adjusted P/E"),
        ("EV/EBITDA", f"{ev_ebitda:.2f}" if ev_ebitda is not None else "N/A", "Enterprise value multiple"),
        ("Price/Sales", f"{price_to_sales:.2f}" if price_to_sales is not None else "N/A", "Revenue multiple"),
        (
            "Dividend Yield",
            format_percentage(dividend_yield * 100) if dividend_yield else "N/A",
            "Annual income return",
        ),
    ]

    columns = responsive_columns(len(metrics), max_cols=3)
    for index, (label, value, note) in enumerate(metrics):
        with columns[index % len(columns)]:
            st.metric(label, value)
            st.caption(note)
