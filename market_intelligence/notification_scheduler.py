"""
market_intelligence/notification_scheduler.py

Purpose: Orchestrates every periodic notification-generating check in
one place. Streamlit itself has no background job runner, so this
module is designed to be invoked externally on a schedule -- e.g. a
cron job (Linux/macOS) or Windows Task Scheduler running:

    python -m market_intelligence.notification_scheduler --task price_alerts
    python -m market_intelligence.notification_scheduler --task all

This mirrors how `database/init_db.py` is a standalone script rather
than something the Streamlit app calls itself; the two follow the same
"real script, real entry point, PyCharm Run-configuration-friendly"
pattern already established in Phase 1.
"""

import argparse
import sys
from datetime import datetime, timedelta

from dashboard.market_data_service import MARKET_INDICES, fetch_quote, get_market_status
from database.prediction_service import prediction_service
from database.user_service import user_service
from logging_config import logger
from market_intelligence.email_notification import send_daily_digest_email, send_weekly_digest_email
from market_intelligence.ipo_alerts import check_ipo_status_changes
from market_intelligence.news_alerts import check_watchlist_breaking_news
from market_intelligence.notification_service import create_notification, get_notifications, should_notify
from market_intelligence.price_alerts import check_all_price_alerts
from market_intelligence.watchlist_alerts import check_watchlist_price_moves

PROFIT_TARGET_PCT = 20.0
STOP_LOSS_PCT = -10.0
CRASH_THRESHOLD_PCT = -3.0
RALLY_THRESHOLD_PCT = 3.0
PREDICTION_CHANGE_THRESHOLD_PCT = 5.0


def _already_notified_today(user_id: int, notification_type: str) -> bool:
    """Prevent duplicate once-per-day notifications (market open/close, crash/rally) across repeated runs."""
    today_notifications = get_notifications(user_id, include_archived=True, page_size=50)["items"]
    today = datetime.utcnow().date()
    return any(n.notification_type == notification_type and n.created_at.date() == today for n in today_notifications)


def check_market_open_close() -> int:
    """Notify subscribed users once per day when the market opens and once when it closes."""
    status = get_market_status()
    notification_type = "MARKET_OPEN" if status["is_open"] else "MARKET_CLOSED"
    category = "market_opening" if status["is_open"] else "market_closing"

    notified_count = 0
    for user in user_service.list_active_users(page_size=1000)["items"]:
        if not should_notify(user.user_id, category):
            continue
        if _already_notified_today(user.user_id, notification_type):
            continue
        create_notification(
            user_id=user.user_id,
            notification_type=notification_type,
            title="Market " + ("Open" if status["is_open"] else "Closed"),
            message=f"The market is now {status['label'].lower()} as of {status['as_of'].strftime('%I:%M %p')} IST.",
            priority="LOW",
        )
        notified_count += 1

    logger.info(f"Market open/close check complete: {notified_count} notification(s) created.")
    return notified_count


def check_market_crash_rally() -> int:
    """Notify subscribed users of a large single-day NIFTY 50 move (crash or rally)."""
    quote = fetch_quote(MARKET_INDICES["NIFTY 50"])
    if quote is None:
        return 0

    change_pct = quote["change_pct"]
    if change_pct > CRASH_THRESHOLD_PCT and change_pct < RALLY_THRESHOLD_PCT:
        return 0

    is_crash = change_pct <= CRASH_THRESHOLD_PCT
    notification_type = "MARKET_CRASH" if is_crash else "MARKET_RALLY"

    notified_count = 0
    for user in user_service.list_active_users(page_size=1000)["items"]:
        if not should_notify(user.user_id, "market_crash_rally"):
            continue
        if _already_notified_today(user.user_id, notification_type):
            continue
        create_notification(
            user_id=user.user_id,
            notification_type=notification_type,
            title="Market Crash Alert" if is_crash else "Market Rally Alert",
            message=f"NIFTY 50 has moved {change_pct:+.2f}% today -- a significant {'decline' if is_crash else 'rally'}.",
            priority="HIGH",
        )
        notified_count += 1

    logger.info(f"Market crash/rally check complete: {notified_count} notification(s) created.")
    return notified_count


def check_portfolio_targets() -> int:
    """
    Notify users when a holding crosses a generic profit-target or
    stop-loss threshold. FinSight AI doesn't currently store a
    per-holding custom target/stop-loss (no such column exists on
    `portfolio`, and adding one wasn't judged "absolutely necessary"
    for this phase), so a sensible fixed policy is used instead:
    +20% profit or -10% loss versus average buy price.
    """
    from database.portfolio_service import portfolio_service

    notified_count = 0
    for user in user_service.list_active_users(page_size=1000)["items"]:
        wants_profit = should_notify(user.user_id, "portfolio_profit_target")
        wants_loss = should_notify(user.user_id, "portfolio_stop_loss")
        if not wants_profit and not wants_loss:
            continue

        summary = portfolio_service.portfolio_summary(user.user_id)
        for holding in summary["holdings"]:
            pnl_pct = holding["profit_loss_pct"]
            if wants_profit and pnl_pct >= PROFIT_TARGET_PCT:
                if _already_notified_today(user.user_id, "PORTFOLIO_PROFIT_TARGET"):
                    continue
                create_notification(
                    user_id=user.user_id, notification_type="PORTFOLIO_PROFIT_TARGET",
                    title=f"Profit Target Reached: {holding['ticker_symbol']}",
                    message=f"{holding['ticker_symbol']} is up {pnl_pct:.2f}% from your average buy price.",
                    priority="MEDIUM", related_ticker=holding["ticker_symbol"],
                )
                notified_count += 1
            elif wants_loss and pnl_pct <= STOP_LOSS_PCT:
                if _already_notified_today(user.user_id, "PORTFOLIO_STOP_LOSS"):
                    continue
                create_notification(
                    user_id=user.user_id, notification_type="PORTFOLIO_STOP_LOSS",
                    title=f"Stop-Loss Warning: {holding['ticker_symbol']}",
                    message=f"{holding['ticker_symbol']} is down {abs(pnl_pct):.2f}% from your average buy price.",
                    priority="HIGH", related_ticker=holding["ticker_symbol"],
                )
                notified_count += 1

    logger.info(f"Portfolio target check complete: {notified_count} notification(s) created.")
    return notified_count


def check_prediction_changes() -> int:
    """Notify users when a new ML prediction differs meaningfully from their prior prediction for the same ticker/model/horizon."""
    notified_count = 0
    for user in user_service.list_active_users(page_size=1000)["items"]:
        if not should_notify(user.user_id, "prediction_changes"):
            continue

        recent = prediction_service.get_user_predictions(user.user_id, page_size=50)["items"]
        grouped: dict[tuple[str, str, int], list] = {}
        for entry in recent:
            key = (entry.ticker_symbol, entry.model_name, entry.prediction_horizon_days)
            grouped.setdefault(key, []).append(entry)

        for (ticker, model_name, horizon), entries in grouped.items():
            entries.sort(key=lambda e: e.created_at, reverse=True)
            if len(entries) < 2:
                continue
            latest, previous = entries[0], entries[1]
            change_pct = abs((float(latest.predicted_price) - float(previous.predicted_price)) / float(previous.predicted_price)) * 100
            if change_pct < PREDICTION_CHANGE_THRESHOLD_PCT:
                continue

            create_notification(
                user_id=user.user_id, notification_type="PREDICTION_CHANGE",
                title=f"Prediction Update: {ticker}",
                message=(
                    f"Your {model_name} {horizon}-day prediction for {ticker} changed from "
                    f"{float(previous.predicted_price):,.2f} to {float(latest.predicted_price):,.2f} "
                    f"({change_pct:.1f}% difference)."
                ),
                priority="LOW", related_ticker=ticker,
            )
            notified_count += 1

    logger.info(f"Prediction change check complete: {notified_count} notification(s) created.")
    return notified_count


def send_daily_digests() -> int:
    """Send a daily digest email to every user who has opted in and has new notifications."""
    sent_count = 0
    cutoff = datetime.utcnow() - timedelta(hours=24)
    for user in user_service.list_active_users(page_size=1000)["items"]:
        if not should_notify(user.user_id, "email_daily_digest"):
            continue
        recent = get_notifications(user.user_id, include_archived=True, page_size=100)["items"]
        recent = [n for n in recent if n.created_at >= cutoff]
        if not recent:
            continue
        payload = [{"title": n.title, "message": n.message} for n in recent]
        if send_daily_digest_email(user.email, payload):
            sent_count += 1
    logger.info(f"Daily digest run complete: {sent_count} email(s) sent.")
    return sent_count


def send_weekly_digests() -> int:
    """Send a weekly digest email to every user who has opted in and has new notifications."""
    sent_count = 0
    cutoff = datetime.utcnow() - timedelta(days=7)
    for user in user_service.list_active_users(page_size=1000)["items"]:
        if not should_notify(user.user_id, "email_weekly_digest"):
            continue
        recent = get_notifications(user.user_id, include_archived=True, page_size=200)["items"]
        recent = [n for n in recent if n.created_at >= cutoff]
        if not recent:
            continue
        payload = [{"title": n.title, "message": n.message} for n in recent]
        if send_weekly_digest_email(user.email, payload):
            sent_count += 1
    logger.info(f"Weekly digest run complete: {sent_count} email(s) sent.")
    return sent_count


TASKS = {
    "price_alerts": check_all_price_alerts,
    "watchlist_alerts": check_watchlist_price_moves,
    "news_alerts": check_watchlist_breaking_news,
    "ipo_alerts": check_ipo_status_changes,
    "market_open_close": check_market_open_close,
    "market_crash_rally": check_market_crash_rally,
    "portfolio_targets": check_portfolio_targets,
    "prediction_changes": check_prediction_changes,
    "daily_digest": send_daily_digests,
    "weekly_digest": send_weekly_digests,
}


def run_all_checks() -> dict[str, int]:
    """Run every check task in sequence and return a summary of counts."""
    results: dict[str, int] = {}
    for name, task_fn in TASKS.items():
        if name in ("daily_digest", "weekly_digest"):
            continue  # digests are run on their own schedule, not with every "all" pass
        try:
            results[name] = task_fn()
        except Exception as exc:  # noqa: BLE001 - one task's failure must not stop the others
            logger.error(f"Scheduler task '{name}' failed: {exc}")
            results[name] = -1
    return results


def main() -> None:
    """CLI entry point: `python -m market_intelligence.notification_scheduler --task <name>`."""
    parser = argparse.ArgumentParser(description="FinSight AI notification scheduler")
    parser.add_argument("--task", choices=list(TASKS.keys()) + ["all"], default="all")
    args = parser.parse_args()

    if args.task == "all":
        results = run_all_checks()
        print("Scheduler run complete:", results)
    else:
        count = TASKS[args.task]()
        print(f"Task '{args.task}' complete: {count} notification(s)/email(s) processed.")


if __name__ == "__main__":
    main()
    sys.exit(0)
