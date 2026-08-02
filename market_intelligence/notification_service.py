"""
market_intelligence/notification_service.py

Purpose: The core service for the in-app Notification Center
(`notifications` table) and per-category subscription preferences
(`notification_preferences` table), both new in Phase 8. Every other
alert-generating file (watchlist_alerts.py, price_alerts.py,
news_alerts.py, ipo_alerts.py, notification_scheduler.py) creates
notifications through this module rather than touching the tables
directly, and checks `should_notify()` first so a user's preferences
are always respected.
"""

from typing import Any

from database.base_service import BaseService
from database.models import Notification, NotificationPreference
from database.settings_service import settings_service
from logging_config import logger

VALID_PRIORITIES = ("LOW", "MEDIUM", "HIGH")


class NotificationService(BaseService[Notification]):
    """CRUD for the `notifications` table (the in-app Notification Center)."""

    model = Notification
    pk_column = "notification_id"


class NotificationPreferenceService(BaseService[NotificationPreference]):
    """CRUD for the `notification_preferences` table."""

    model = NotificationPreference
    pk_column = "preference_id"


notification_service = NotificationService()
notification_preference_service = NotificationPreferenceService()


# ==========================================================
# Preferences
# ==========================================================
def get_preferences(user_id: int) -> NotificationPreference:
    """Fetch a user's notification preferences, creating a default row if none exists yet."""
    existing = notification_preference_service.find_one_by(user_id=user_id)
    if existing is not None:
        return existing
    created = notification_preference_service.create(NotificationPreference(user_id=user_id))
    logger.info(f"Default notification preferences created for user_id={user_id}")
    return created


def update_preferences(user_id: int, **updates: bool) -> NotificationPreference:
    """Update one or more of a user's notification preference toggles."""
    preferences = get_preferences(user_id)
    valid_fields = {c.name for c in NotificationPreference.__table__.columns}
    filtered_updates = {key: value for key, value in updates.items() if key in valid_fields}
    return notification_preference_service.update(preferences.preference_id, filtered_updates)


def should_notify(user_id: int, category_field: str) -> bool:
    """
    Return True if a user should receive a notification for the given
    category, respecting both the granular per-category toggle and the
    Phase 1 master `settings.notifications_enabled` switch.
    """
    settings = settings_service.get_or_create(user_id)
    if not settings.notifications_enabled:
        return False

    preferences = get_preferences(user_id)
    return bool(getattr(preferences, category_field, True))


# ==========================================================
# Notification Center CRUD
# ==========================================================
def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    priority: str = "MEDIUM",
    related_ticker: str | None = None,
) -> Notification:
    """Create a new in-app notification for a user."""
    if priority not in VALID_PRIORITIES:
        priority = "MEDIUM"

    entry = notification_service.create(
        Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title.strip(),
            message=message.strip(),
            priority=priority,
            related_ticker=related_ticker,
        )
    )
    logger.info(f"Notification created: user_id={user_id}, type={notification_type}, priority={priority}")
    return entry


def get_notifications(
    user_id: int, unread_only: bool = False, include_archived: bool = False, page: int = 1, page_size: int = 20
) -> dict[str, Any]:
    """List a user's notifications, newest first, with optional unread/archived filters."""
    filters: dict[str, Any] = {"user_id": user_id}
    if unread_only:
        filters["is_read"] = False
    if not include_archived:
        filters["is_archived"] = False
    return notification_service.list(
        filters=filters, sort_by="created_at", sort_direction="desc", page=page, page_size=page_size
    )


def get_unread_count(user_id: int) -> int:
    """Return the count of unread, non-archived notifications for a user (for a sidebar badge)."""
    return notification_service.count(filters={"user_id": user_id, "is_read": False, "is_archived": False})


def mark_read(notification_id: int) -> Notification:
    """Mark a single notification as read."""
    return notification_service.update(notification_id, {"is_read": True})


def mark_all_read(user_id: int) -> int:
    """Mark every unread notification for a user as read. Returns the count updated."""
    unread = notification_service.list(filters={"user_id": user_id, "is_read": False}, page_size=500)["items"]
    for entry in unread:
        notification_service.update(entry.notification_id, {"is_read": True})
    return len(unread)


def archive_notification(notification_id: int) -> Notification:
    """Archive a notification (hides it from the default view without deleting it)."""
    return notification_service.update(notification_id, {"is_archived": True})


def delete_notification(notification_id: int) -> None:
    """Permanently delete a notification."""
    notification_service.delete(notification_id)
