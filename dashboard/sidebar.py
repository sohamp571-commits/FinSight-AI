"""
dashboard/sidebar.py

Purpose: Dashboard-specific sidebar controls -- manual refresh,
auto-refresh interval, and a compact market-status readout. This is
additive to (not a replacement for) the global sidebar rendered by
`app.py`'s `_render_sidebar()` (identity/navigation/logout); it is
called from `dashboard.py`'s `render()` and draws into the same
`st.sidebar` container, appearing below the global controls.
"""

import streamlit as st

from dashboard.market_data_service import get_market_status
from logging_config import logger


def render_dashboard_sidebar() -> None:
    """Render dashboard-only sidebar controls: refresh, auto-refresh, and status."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📈 Market Dashboard")

        status = get_market_status()
        status_icon = "🟢" if status["is_open"] else "🔴"
        st.caption(f"{status_icon} {status['label']} • {status['as_of'].strftime('%I:%M %p')} IST")

        if st.button("🔄 Refresh Data", use_container_width=True, key="dashboard_refresh_btn"):
            st.cache_data.clear()
            logger.info("Dashboard cache cleared via manual refresh.")
            st.rerun()

        auto_refresh = st.checkbox(
            "Auto-refresh every 60s", value=st.session_state.get("dashboard_auto_refresh", False)
        )
        st.session_state["dashboard_auto_refresh"] = auto_refresh

        if auto_refresh:
            st.caption("Auto-refresh is on. The dashboard will update on your next interaction cycle.")


def maybe_auto_refresh() -> None:
    """
    If auto-refresh is enabled, pause briefly and trigger a rerun.
    Kept as a separate opt-in call (invoked at the end of dashboard.py's
    render) so it never blocks the initial page load.
    """
    if st.session_state.get("dashboard_auto_refresh"):
        import time

        time.sleep(60)
        st.rerun()
