"""
market_intelligence/ipo_details.py

Purpose: Renders a detailed view for a single selected IPO -- every
field from `ipo_listings` plus a "Notify me" action that wires into
notification_service.py (Phase 8's notification center), so a user
can subscribe to updates for a specific IPO without waiting for the
next scheduled digest.
"""

import streamlit as st

from custom_exceptions import FinSightBaseException
from helper import format_currency, format_date
from logging_config import logger
from market_intelligence.ipo_service import ipo_service
from market_intelligence.notification_service import create_notification

_STATUS_BADGE = {
    "UPCOMING": "🗓️ Upcoming", "OPEN": "🟢 Open for Subscription", "CLOSED": "🔴 Closed", "LISTED": "✅ Listed",
}


def render_ipo_details(user_id: int) -> None:
    """Render the IPO Details tab: a picker plus the full detail card for the selected IPO."""
    all_ipos = ipo_service.list(page_size=200, sort_by="open_date", sort_direction="desc")["items"]
    if not all_ipos:
        st.info("No IPOs available yet. Visit the IPO Calendar tab first to load sample data.")
        return

    options = {f"{ipo.company_name} ({ipo.status.title()})": ipo.ipo_id for ipo in all_ipos}
    selected_label = st.selectbox("Select an IPO", list(options.keys()), key="ipo_details_selector")
    ipo = ipo_service.get_by_id(options[selected_label])

    st.markdown(f"## {ipo.company_name}")
    st.markdown(f"**Status:** {_STATUS_BADGE.get(ipo.status, ipo.status)}  •  **Exchange:** {ipo.exchange}")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Issue Price Band**")
        st.write(
            f"{format_currency(ipo.issue_price_min, '₹')} – {format_currency(ipo.issue_price_max, '₹')}"
            if ipo.issue_price_min and ipo.issue_price_max else "Not yet announced"
        )
        st.markdown("**Lot Size**")
        st.write(f"{ipo.lot_size} shares" if ipo.lot_size else "Not yet announced")
        st.markdown("**Grey Market Premium (GMP)**")
        st.write(format_currency(ipo.gmp, "₹") if ipo.gmp is not None else "Not available")
    with col2:
        st.markdown("**Open Date**")
        st.write(format_date(ipo.open_date) if ipo.open_date else "TBA")
        st.markdown("**Close Date**")
        st.write(format_date(ipo.close_date) if ipo.close_date else "TBA")
        st.markdown("**Listing Date**")
        st.write(format_date(ipo.listing_date) if ipo.listing_date else "TBA")

    if ipo.subscription_times is not None:
        st.markdown("---")
        st.markdown(f"### 📊 Subscribed {float(ipo.subscription_times):.2f}x")
        st.progress(min(1.0, float(ipo.subscription_times) / 100))

    st.markdown("---")
    if st.button("🔔 Notify me about this IPO", key=f"notify_ipo_{ipo.ipo_id}", use_container_width=True):
        try:
            create_notification(
                user_id=user_id,
                notification_type="IPO_WATCH",
                title=f"Watching {ipo.company_name}",
                message=f"You'll be notified of status changes for the {ipo.company_name} IPO.",
                priority="LOW",
                related_ticker=ipo.ticker_symbol,
            )
            st.success(f"You'll now be notified about updates to {ipo.company_name}.")
        except FinSightBaseException as exc:
            logger.error(f"Failed to create IPO watch notification: {exc}")
            st.error("Could not set up the notification right now.")
