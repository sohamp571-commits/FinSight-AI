"""
stock_search/fundamental_analysis.py

Purpose: Computes and renders fundamental ratios that require pulling
the income statement and balance sheet -- ROE, ROA, Debt-to-Equity,
Current Ratio, Quick Ratio, Operating Margin, and Net Margin -- plus
EPS and Dividend Yield for completeness. Reuses
`income_statement.get_income_statement()` and
`balance_sheet.get_balance_sheet()` rather than issuing new yfinance
calls, and `utils.safe_divide` to avoid division-by-zero crashes on
incomplete data.
"""

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.dashboard_layout import render_section_header, responsive_columns
from helper import format_currency, format_percentage
from stock_search.balance_sheet import get_balance_sheet
from stock_search.company_profile import get_company_info
from stock_search.income_statement import get_income_statement
from utils import safe_divide


def _latest(df: pd.DataFrame | None, row_name: str) -> float | None:
    """Safely pull the most recent period's value for a given row label."""
    if df is None or row_name not in df.index:
        return None
    series = df.loc[row_name].dropna()
    return float(series.iloc[0]) if not series.empty else None


def _compute_ratios(ticker: str) -> dict[str, Any]:
    """Compute every fundamental ratio for a ticker from its info/income/balance-sheet data."""
    info = get_company_info(ticker) or {}
    income_stmt = get_income_statement(ticker)
    balance = get_balance_sheet(ticker)

    net_income = _latest(income_stmt, "Net Income")
    total_revenue = _latest(income_stmt, "Total Revenue")
    operating_income = _latest(income_stmt, "Operating Income")

    total_equity = _latest(balance, "Total Equity Gross Minority Interest")
    total_assets = _latest(balance, "Total Assets")
    total_debt = _latest(balance, "Total Debt")
    current_assets = _latest(balance, "Current Assets")
    current_liabilities = _latest(balance, "Current Liabilities")
    inventory = _latest(balance, "Inventory")

    return {
        "roe_pct": safe_divide(net_income, total_equity, default=None) * 100 if net_income and total_equity else None,
        "roa_pct": safe_divide(net_income, total_assets, default=None) * 100 if net_income and total_assets else None,
        "debt_to_equity": safe_divide(total_debt, total_equity, default=None) if total_debt and total_equity else None,
        "current_ratio": safe_divide(current_assets, current_liabilities, default=None)
        if current_assets and current_liabilities
        else None,
        "quick_ratio": safe_divide((current_assets or 0) - (inventory or 0), current_liabilities, default=None)
        if current_assets and current_liabilities
        else None,
        "operating_margin_pct": safe_divide(operating_income, total_revenue, default=None) * 100
        if operating_income and total_revenue
        else None,
        "net_margin_pct": safe_divide(net_income, total_revenue, default=None) * 100
        if net_income and total_revenue
        else None,
        "eps": info.get("trailingEps"),
        "dividend_yield_pct": (info.get("dividendYield") * 100) if info.get("dividendYield") else None,
        "currency": "₹" if (".NS" in ticker or ".BO" in ticker) else "$",
    }


def render_fundamental_analysis(ticker: str) -> None:
    """Render the Fundamental Analysis section: computed ratios with plain-English context."""
    render_section_header("Fundamental Analysis", icon="🔬")

    ratios = _compute_ratios(ticker)
    currency = ratios["currency"]

    def _pct(value: float | None) -> str:
        return format_percentage(value) if value is not None else "N/A"

    def _ratio(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "N/A"

    rows: list[tuple[str, str]] = [
        ("Return on Equity (ROE)", _pct(ratios["roe_pct"])),
        ("Return on Assets (ROA)", _pct(ratios["roa_pct"])),
        ("Debt to Equity", _ratio(ratios["debt_to_equity"])),
        ("Current Ratio", _ratio(ratios["current_ratio"])),
        ("Quick Ratio", _ratio(ratios["quick_ratio"])),
        ("Operating Margin", _pct(ratios["operating_margin_pct"])),
        ("Net Margin", _pct(ratios["net_margin_pct"])),
        ("EPS", format_currency(ratios["eps"], currency) if ratios["eps"] is not None else "N/A"),
        ("Dividend Yield", _pct(ratios["dividend_yield_pct"])),
    ]

    if all(value == "N/A" for _, value in rows):
        st.info(f"Fundamental ratio data is not available for {ticker} (financial statements may be limited).")
        return

    for row_start in range(0, len(rows), 3):
        row = rows[row_start:row_start + 3]
        columns = responsive_columns(len(row), max_cols=3)
        for column, (label, value) in zip(columns, row):
            with column:
                st.metric(label, value)
