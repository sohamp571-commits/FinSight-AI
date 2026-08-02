"""
market_intelligence/price_alerts.py

Purpose: Bridges the *existing* `alerts` table (Phase 3
`database.alert_service` -- user-defined price/percent-change alerts,
reused here with zero schema changes) to the new Notification Center.
Evaluates every user's active alerts against live prices and, when a
condition triggers, creates an in-app notification and (if the user
has opted in) sends an instant email.
"""

from dashboard.market_data_service import fetch_quote
from database.alert_service import alert_service
from database.models import Alert
from database.user_service import user_service
from logging_config import logger
from market_intelligence.email_notification import send_instant_alert_email
from market_intelligence.notification_service import create_notification, should_notify

_CONDITION_LABEL = {
    "PRICE_ABOVE": "rose above",
    "PRICE_BELOW": "fell below",
    "PERCENT_CHANGE": "moved by at least",
}


def _notify_for_alert(alert: Alert, current_price: float) -> None:
    """Create a notification (and optionally an email) for one newly-triggered alert."""
    condition_text = _CONDITION_LABEL.get(alert.condition_type, "hit its target for")
    title = f"Price Alert: {alert.ticker_symbol}"
    message = (
        f"{alert.ticker_symbol} {condition_text} your target of {float(alert.target_value):,.2f} "
        f"(current price: {current_price:,.2f})."
    )

    create_notification(
        user_id=alert.user_id,
        notification_type="WATCHLIST_PRICE_ALERT",
        title=title,
        message=message,
        priority="HIGH",
        related_ticker=alert.ticker_symbol,
    )

    if should_notify(alert.user_id, "watchlist_price_alerts") and should_notify(alert.user_id, "email_instant_alerts"):
        try:
            user = user_service.get_by_id(alert.user_id)
            send_instant_alert_email(user.email, title, message)
        except Exception as exc:  # noqa: BLE001 - email failure must never break alert checking
            logger.error(f"Failed to send price alert email for alert_id={alert.alert_id}: {exc}")


def check_all_price_alerts() -> int:
    """
    Evaluate every active, untriggered alert across all users against a
    live quote. Intended to be invoked periodically by
    notification_scheduler.py (e.g. every few minutes during market hours).

    Returns:
        The number of alerts that triggered during this run.
    """
    active_alerts = alert_service.list(filters={"is_active": True}, page_size=1000)["items"]
    untriggered = [a for a in active_alerts if not a.is_triggered]

    triggered_count = 0
    tickers_checked: dict[str, float | None] = {}

    for alert in untriggered:
        if alert.ticker_symbol not in tickers_checked:
            quote = fetch_quote(alert.ticker_symbol)
            tickers_checked[alert.ticker_symbol] = quote["price"] if quote else None

        current_price = tickers_checked[alert.ticker_symbol]
        if current_price is None:
            continue

        previous_close = None
        if alert.condition_type == "PERCENT_CHANGE":
            quote = fetch_quote(alert.ticker_symbol)
            previous_close = quote["previous_close"] if quote else None

        if alert_service.evaluate_and_trigger(alert, current_price, previous_close):
            _notify_for_alert(alert, current_price)
            triggered_count += 1

    if triggered_count:
        logger.info(f"Price alert check complete: {triggered_count} alert(s) triggered.")
    return triggered_count
