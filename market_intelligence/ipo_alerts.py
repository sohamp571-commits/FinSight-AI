"""
market_intelligence/ipo_alerts.py

Purpose: Detects IPO status transitions (Upcoming -> Open, Open ->
Closed, Closed -> Listed) via `ipo_service.refresh_all_statuses()` and
notifies every user subscribed to the relevant category
(`ipo_open`/`ipo_close`/`ipo_listing` in notification_preferences).
"""

from database.user_service import user_service
from logging_config import logger
from market_intelligence.ipo_service import ipo_service
from market_intelligence.notification_service import create_notification, should_notify

_STATUS_TO_CATEGORY = {"OPEN": "ipo_open", "CLOSED": "ipo_close", "LISTED": "ipo_listing"}
_STATUS_TO_MESSAGE = {
    "OPEN": "is now open for subscription",
    "CLOSED": "has closed for subscription",
    "LISTED": "has listed on the exchange",
}


def _get_all_active_user_ids() -> list[int]:
    """Return every active, non-deleted user's ID (candidates for a broadcast IPO notification)."""
    active_users = user_service.list_active_users(page_size=1000)["items"]
    return [user.user_id for user in active_users]


def check_ipo_status_changes() -> int:
    """
    Refresh every IPO's status and broadcast a notification to every
    subscribed user for each transition detected this run. Intended to
    be invoked periodically (e.g. once daily) by notification_scheduler.py.

    Returns:
        The number of notifications created during this run.
    """
    # Snapshot statuses before refreshing so we know exactly which ones changed.
    before = {ipo.ipo_id: ipo.status for ipo in ipo_service.list(page_size=500)["items"]}
    ipo_service.refresh_all_statuses()
    after = ipo_service.list(page_size=500)["items"]

    changed = [ipo for ipo in after if before.get(ipo.ipo_id) != ipo.status and ipo.status in _STATUS_TO_CATEGORY]
    if not changed:
        return 0

    active_user_ids = _get_all_active_user_ids()
    notified_count = 0

    for ipo in changed:
        category = _STATUS_TO_CATEGORY[ipo.status]
        message = f"{ipo.company_name} {_STATUS_TO_MESSAGE[ipo.status]}."

        for user_id in active_user_ids:
            if not should_notify(user_id, category):
                continue
            create_notification(
                user_id=user_id,
                notification_type=f"IPO_{ipo.status}",
                title=f"IPO Update: {ipo.company_name}",
                message=message,
                priority="MEDIUM",
                related_ticker=ipo.ticker_symbol,
            )
            notified_count += 1

    logger.info(f"IPO status check complete: {len(changed)} IPO(s) changed, {notified_count} notification(s) created.")
    return notified_count
