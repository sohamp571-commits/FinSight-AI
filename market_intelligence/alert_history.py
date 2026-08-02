"""
market_intelligence/alert_history.py

Purpose: Renders a combined "Alert History" view -- every notification
ever generated for a user (Notification Center, new in Phase 8) side
by side with their configured price alerts and trigger status (Phase 3
`database.alert_service`, reused unchanged). Gives one page to audit
everything that has or could have notified the user.
"""

import streamlit as st

from database.alert_service import alert_service
from dashboard.dashboard_layout import render_section_header
from helper import format_datetime
from market_intelligence.notification_service import get_notifications

_PRIORITY_ICON = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}


def render_alert_history(user_id: int) -> None:
    """Render the Alert History tab: notification history + configured price alerts."""
    render_section_header("Alert History", icon="🕒")

    notif_tab, price_alert_tab = st.tabs(["Notification History", "Configured Price Alerts"])

    with notif_tab:
        result = get_notifications(user_id, include_archived=True, page_size=50)
        notifications = result["items"]
        if not notifications:
            st.info("No notifications yet.")
        else:
            rows = [
                {
                    "Priority": _PRIORITY_ICON.get(n.priority, "⚪") + " " + n.priority,
                    "Type": n.notification_type.replace("_", " ").title(),
                    "Title": n.title,
                    "Ticker": n.related_ticker or "—",
                    "Status": "Archived" if n.is_archived else ("Read" if n.is_read else "Unread"),
                    "Created": format_datetime(n.created_at),
                }
                for n in notifications
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    with price_alert_tab:
        alerts_result = alert_service.get_user_alerts(user_id, page_size=50)
        alerts = alerts_result["items"]
        if not alerts:
            st.info("No price alerts configured yet.")
        else:
            rows = [
                {
                    "Ticker": a.ticker_symbol,
                    "Condition": a.condition_type.replace("_", " ").title(),
                    "Target": f"{float(a.target_value):,.2f}",
                    "Status": "Triggered" if a.is_triggered else ("Active" if a.is_active else "Inactive"),
                    "Triggered At": format_datetime(a.triggered_at) if a.triggered_at else "—",
                    "Created": format_datetime(a.created_at),
                }
                for a in alerts
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
