"""
stock_search/financials.py

Purpose: Orchestrates the "Financial Statements" section by combining
income_statement.py, balance_sheet.py, and cash_flow.py into a single
sub-tabbed view, matching the requirement for Income Statement,
Balance Sheet, Cash Flow, Quarterly Results, and Annual Results all
being reachable from one place (the annual/quarterly toggle lives
inside each individual statement's radio control).
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header
from stock_search.balance_sheet import render_balance_sheet
from stock_search.cash_flow import render_cash_flow
from stock_search.income_statement import render_income_statement


def render_financials(ticker: str) -> None:
    """Render the Financials tab with sub-tabs for each statement type."""
    render_section_header("Financial Statements", subtitle=f"{ticker} — Annual & Quarterly", icon="📚")

    income_tab, balance_tab, cash_flow_tab = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
    with income_tab:
        render_income_statement(ticker)
    with balance_tab:
        render_balance_sheet(ticker)
    with cash_flow_tab:
        render_cash_flow(ticker)
