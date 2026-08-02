"""
stock_search/stock_search.py

Purpose: The main entry point for the Stock Search & Company Analysis
module. Ties together every other file in this package: the search
bar (with autocomplete suggestions and recent-search history), the
"favorite" toggle (backed by the existing watchlist), invalid-ticker
handling, and the tabbed dispatch into Profile / Statistics /
Valuation / Fundamentals / Financials / Historical Data / Comparison.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException, ValidationError
from database.audit_service import audit_service
from dashboard.dashboard_layout import inject_dashboard_css, render_divider
from logging_config import logger
from stock_search.company_profile import render_company_profile
from stock_search.financials import render_financials
from stock_search.fundamental_analysis import render_fundamental_analysis
from stock_search.historical_data import render_historical_data
from stock_search.search_service import (
    clear_search_history,
    get_autocomplete_suggestions,
    get_recent_searches,
    is_favorite,
    log_search,
    resolve_ticker,
    toggle_favorite,
    validate_ticker_exists,
)
from stock_search.stock_comparison import render_stock_comparison
from stock_search.stock_statistics import render_stock_statistics
from stock_search.valuation_metrics import render_valuation_metrics

_ANALYSIS_TABS = [
    ("Profile", render_company_profile),
    ("Statistics", render_stock_statistics),
    ("Valuation", render_valuation_metrics),
    ("Fundamentals", render_fundamental_analysis),
    ("Financials", render_financials),
    ("Historical Data", render_historical_data),
]


def _render_search_bar(user_id: int) -> str | None:
    """
    Render the search input with live autocomplete suggestions.
    Returns the resolved ticker to analyze, or None if nothing has
    been searched yet this render.
    """
    query = st.text_input(
        "🔍 Search by company name, NSE symbol, or BSE symbol",
        placeholder="e.g. Reliance Industries, TCS, INFY.NS, AAPL",
        key="stock_search_query",
    )

    if query.strip():
        suggestions = get_autocomplete_suggestions(query, limit=6)
        if suggestions:
            suggestion_labels = [f"{s['name']} ({s['ticker']})" for s in suggestions]
            st.caption("Suggestions: " + "  •  ".join(suggestion_labels))

    if not query.strip():
        return None

    ticker = resolve_ticker(query)
    if not validate_ticker_exists(ticker):
        st.error(f"'{query}' could not be resolved to a valid, actively-traded ticker. Please check the spelling.")
        logger.warning(f"Invalid ticker search by user_id={user_id}: query='{query}' -> resolved='{ticker}'")
        return None

    log_search(user_id, query, ticker)
    return ticker


def _render_recent_searches_and_favorite(user_id: int, ticker: str | None) -> None:
    """Render the recent-searches sidebar section and the favorite toggle for the active ticker."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🕓 Recent Searches")
        recent = get_recent_searches(user_id, limit=8)
        if not recent:
            st.caption("No recent searches yet.")
        else:
            for entry in recent:
                label = entry.ticker_symbol or entry.search_query
                if st.button(label, key=f"recent_{entry.search_id}", use_container_width=True):
                    st.session_state["stock_search_query"] = entry.ticker_symbol or entry.search_query
                    st.rerun()
            if st.button("Clear History", use_container_width=True, key="clear_search_history_btn"):
                cleared = clear_search_history(user_id)
                st.success(f"Cleared {cleared} search history entr{'y' if cleared == 1 else 'ies'}.")
                st.rerun()

    if ticker:
        currently_favorite = is_favorite(user_id, ticker)
        button_label = "★ Remove from Favorites" if currently_favorite else "☆ Add to Favorites"
        if st.button(button_label, key="favorite_toggle_btn"):
            try:
                now_favorite = toggle_favorite(user_id, ticker)
                st.success(f"{ticker} {'added to' if now_favorite else 'removed from'} your favorites.")
                st.rerun()
            except ValidationError as exc:
                st.warning(exc.message)


@login_required
def render() -> None:
    """Render the full Stock Search & Company Analysis page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("🔎 Stock Search & Company Analysis")
        st.caption("Search any NSE/BSE-listed or global company to view its full profile, financials, and ratios.")
        render_divider()

        ticker = _render_search_bar(user_id)
        _render_recent_searches_and_favorite(user_id, ticker)

        if ticker is None:
            st.info("Search for a company above to get started, or pick a recent search from the sidebar.")
            return

        audit_service.log_action(action="STOCK_SEARCH", user_id=user_id, entity_type="ticker", details=ticker)

        tab_labels = [label for label, _ in _ANALYSIS_TABS] + ["Comparison"]
        tabs = st.tabs(tab_labels)

        for tab, (_, render_fn) in zip(tabs[:-1], _ANALYSIS_TABS):
            with tab:
                render_fn(ticker)

        with tabs[-1]:
            render_stock_comparison()

    except FinSightBaseException as exc:
        logger.error(f"Handled error in stock search: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in stock search: {exc}")
        st.error("An unexpected error occurred while searching. Please try again.")
