"""
dashboard/dashboard.py

Purpose: The main entry point for the FinSight AI dashboard module.
Ties together every other file in this package: CSS injection, the
authentication guard, the dashboard-specific sidebar, tab navigation,
and dispatch into each tab's content. This is the single function
`app.py` should register in its page routing (see the "Ready for
Phase 5" integration note in the Phase 4 summary).
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_full_name, get_current_user_id
from custom_exceptions import FinSightBaseException
from database.audit_service import audit_service
from dashboard.dashboard_layout import inject_dashboard_css, render_divider
from dashboard.market_heatmap import render_market_heatmap
from dashboard.market_overview import render_overview_tab
from dashboard.most_active import render_most_active
from dashboard.navigation import render_navigation
from dashboard.sidebar import maybe_auto_refresh, render_dashboard_sidebar
from dashboard.top_gainers import render_top_gainers
from dashboard.top_losers import render_top_losers
from logging_config import logger


def _render_gainers_losers_tab() -> None:
    """Render the combined Gainers & Losers tab as two side-by-side sections."""
    left, right = st.columns(2)
    with left:
        render_top_gainers()
    with right:
        render_top_losers()


_TAB_DISPATCH = {
    "overview": render_overview_tab,
    "gainers_losers": _render_gainers_losers_tab,
    "most_active": render_most_active,
    "heatmap": render_market_heatmap,
}


def _log_dashboard_view() -> None:
    """Write an audit_logs entry for this dashboard view (best-effort, never blocks rendering)."""
    user_id = get_current_user_id()
    audit_service.log_action(action="DASHBOARD_VIEW", user_id=user_id, entity_type="dashboard")


@login_required
def render() -> None:
    """
    Render the full Market Dashboard page. Entry point called from
    app.py's router (any authenticated role may view the dashboard --
    it carries no role_required restriction beyond being logged in).
    """
    try:
        inject_dashboard_css()

        full_name = get_current_full_name() or "there"
        st.title(f"📈 Market Dashboard")
        st.caption(f"Welcome back, {full_name}. Live market data updates automatically every 60 seconds.")
        render_divider()

        render_dashboard_sidebar()
        _log_dashboard_view()

        tab_objects, tab_keys = render_navigation()
        for tab, key in zip(tab_objects, tab_keys):
            with tab:
                render_fn = _TAB_DISPATCH.get(key)
                if render_fn is not None:
                    render_fn()

        maybe_auto_refresh()

    except FinSightBaseException as exc:
        logger.error(f"Handled error while rendering dashboard: {exc}")
        st.error(f"Something went wrong loading the dashboard: {exc.message}")
    except Exception as exc:  # noqa: BLE001 - last line of defense for this page
        logger.exception(f"Unexpected error while rendering dashboard: {exc}")
        st.error("An unexpected error occurred while loading the dashboard. Please try refreshing.")
