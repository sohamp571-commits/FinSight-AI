"""
database/settings_service.py

Purpose: Data-layer service for the `settings` table -- one row per
user holding their theme, default currency, and notification
preferences. `get_or_create` is the primary entry point since every
user should have exactly one settings row, created lazily on first
access rather than at registration time (keeps auth_service focused).
"""

from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import Settings
from logging_config import logger

VALID_THEMES = ("light", "dark")
VALID_CURRENCIES = ("INR", "USD", "EUR", "GBP")


class SettingsService(BaseService[Settings]):
    """CRUD operations for the `settings` table."""

    model = Settings
    pk_column = "settings_id"

    def get_or_create(self, user_id: int) -> Settings:
        """Fetch a user's settings row, creating one with defaults if it doesn't exist yet."""
        existing = self.find_one_by(user_id=user_id)
        if existing is not None:
            return existing

        created = self.create(
            Settings(user_id=user_id, theme="light", default_currency="INR", notifications_enabled=True)
        )
        logger.info(f"Default settings created for user_id={user_id}")
        return created

    def set_theme(self, user_id: int, theme: str) -> Settings:
        """Update a user's UI theme preference (light/dark)."""
        theme = theme.strip().lower()
        if theme not in VALID_THEMES:
            raise ValidationError(f"theme must be one of: {', '.join(VALID_THEMES)}")
        settings = self.get_or_create(user_id)
        updated = self.update(settings.settings_id, {"theme": theme})
        logger.info(f"Theme set to '{theme}' for user_id={user_id}")
        return updated

    def set_currency(self, user_id: int, currency: str) -> Settings:
        """Update a user's default display currency."""
        currency = currency.strip().upper()
        if currency not in VALID_CURRENCIES:
            raise ValidationError(f"default_currency must be one of: {', '.join(VALID_CURRENCIES)}")
        settings = self.get_or_create(user_id)
        updated = self.update(settings.settings_id, {"default_currency": currency})
        logger.info(f"Currency set to '{currency}' for user_id={user_id}")
        return updated

    def set_notifications(self, user_id: int, enabled: bool) -> Settings:
        """Enable or disable notifications for a user."""
        settings = self.get_or_create(user_id)
        updated = self.update(settings.settings_id, {"notifications_enabled": enabled})
        logger.info(f"Notifications {'enabled' if enabled else 'disabled'} for user_id={user_id}")
        return updated


settings_service = SettingsService()
