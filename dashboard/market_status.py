"""
dashboard/market_status.py

Purpose: Renders the market-open/closed status indicator shown at the
top of the Overview tab. Pulls its data from
`market_data_service.get_market_status()` and renders it via the
shared badge widget in `dashboard_widgets.py`.
"""

import streamlit as st

from dashboard.dashboard_widgets import render_market_status_badge
from dashboard.market_data_service import get_market_status
from logging_config import logger


def render_market_status_section() -> None:
    """Render the market status badge, degrading gracefully if the status check fails."""
    try:
        status = get_market_status()
        render_market_status_badge(
            is_open=status["is_open"],
            label=status["label"],
            as_of_str=status["as_of"].strftime("%I:%M:%S %p"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to determine market status: {exc}")
        st.caption("Market status unavailable.")
