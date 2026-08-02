"""
database/alert_service.py

Purpose: Data-layer service for the `alerts` table -- user-defined
price/percent-change alerts. Provides CRUD plus activate/deactivate
and trigger-evaluation helpers; the actual background job that polls
prices and fires alerts belongs to a later phase (likely alongside
market_cache_service and a scheduler), but the evaluation logic lives
here since it's pure data-layer arithmetic.
"""

from datetime import datetime
from typing import Any

from constants import AlertCondition
from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import Alert
from logging_config import logger
from utils import validate_positive_number


class AlertService(BaseService[Alert]):
    """CRUD operations for the `alerts` table."""

    model = Alert
    pk_column = "alert_id"

    # ------------------------------------------------------
    # Create
    # ------------------------------------------------------
    def create_alert(self, user_id: int, ticker_symbol: str, condition_type: str, target_value: float) -> Alert:
        """Create a new price/percent-change alert for a user."""
        valid_conditions = {item.value for item in AlertCondition}
        if condition_type not in valid_conditions:
            raise ValidationError(f"condition_type must be one of: {', '.join(sorted(valid_conditions))}")
        validate_positive_number(target_value, "target_value")

        entry = Alert(
            user_id=user_id,
            ticker_symbol=ticker_symbol.strip().upper(),
            condition_type=condition_type,
            target_value=target_value,
            is_triggered=False,
            is_active=True,
        )
        created = self.create(entry)
        logger.info(f"Alert created: user_id={user_id}, ticker={entry.ticker_symbol}, condition={condition_type}")
        return created

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def update_alert(self, alert_id: int, condition_type: str, target_value: float) -> Alert:
        """Update the condition and/or target value of an existing alert (resets trigger state)."""
        valid_conditions = {item.value for item in AlertCondition}
        if condition_type not in valid_conditions:
            raise ValidationError(f"condition_type must be one of: {', '.join(sorted(valid_conditions))}")
        validate_positive_number(target_value, "target_value")

        updated = self.update(
            alert_id,
            {
                "condition_type": condition_type,
                "target_value": target_value,
                "is_triggered": False,
                "triggered_at": None,
            },
        )
        logger.info(f"Alert updated: alert_id={alert_id}")
        return updated

    # ------------------------------------------------------
    # Activate / Deactivate
    # ------------------------------------------------------
    def activate(self, alert_id: int) -> Alert:
        """Re-enable an alert so it will be evaluated again."""
        return self.update(alert_id, {"is_active": True})

    def deactivate(self, alert_id: int) -> Alert:
        """Disable an alert without deleting it."""
        return self.update(alert_id, {"is_active": False})

    # ------------------------------------------------------
    # Delete
    # ------------------------------------------------------
    def delete_alert(self, alert_id: int) -> None:
        """Permanently remove an alert."""
        self.delete(alert_id)
        logger.info(f"Alert deleted: alert_id={alert_id}")

    # ------------------------------------------------------
    # Read
    # ------------------------------------------------------
    def get_user_alerts(
        self, user_id: int, active_only: bool = False, page: int = 1, page_size: int = 50
    ) -> dict[str, Any]:
        """List a user's alerts, optionally restricted to active (non-triggered) ones."""
        filters: dict[str, Any] = {"user_id": user_id}
        if active_only:
            filters["is_active"] = True
        return self.list(filters=filters, sort_by="created_at", sort_direction="desc", page=page, page_size=page_size)

    def get_active_alerts_for_ticker(self, ticker_symbol: str) -> list[Alert]:
        """Fetch every active, untriggered alert for a ticker (used by a future polling job)."""
        result = self.list(
            filters={"ticker_symbol": ticker_symbol.strip().upper(), "is_active": True}, page_size=1000
        )
        return [alert for alert in result["items"] if not alert.is_triggered]

    # ------------------------------------------------------
    # Trigger Evaluation
    # ------------------------------------------------------
    def evaluate_and_trigger(self, alert: Alert, current_price: float, previous_close: float | None = None) -> bool:
        """
        Evaluate a single alert against a current price and mark it
        triggered if its condition is met.

        Returns:
            True if the alert was triggered by this call, False otherwise.
        """
        condition_met = False

        if alert.condition_type == AlertCondition.PRICE_ABOVE.value:
            condition_met = current_price >= float(alert.target_value)
        elif alert.condition_type == AlertCondition.PRICE_BELOW.value:
            condition_met = current_price <= float(alert.target_value)
        elif alert.condition_type == AlertCondition.PERCENT_CHANGE.value and previous_close:
            percent_change = abs((current_price - previous_close) / previous_close) * 100
            condition_met = percent_change >= float(alert.target_value)

        if condition_met:
            self.update(alert.alert_id, {"is_triggered": True, "triggered_at": datetime.utcnow()})
            logger.info(f"Alert triggered: alert_id={alert.alert_id}, ticker={alert.ticker_symbol}")
            return True
        return False


alert_service = AlertService()
