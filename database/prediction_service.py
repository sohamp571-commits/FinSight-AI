"""
database/prediction_service.py

Purpose: Data-layer service for the `prediction_history` table.
Records outputs of the ML prediction module (Phase 5+) so they can be
reviewed later; this phase only provides the storage/query layer, not
the modeling itself.
"""

from typing import Any

from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import PredictionHistory
from logging_config import logger
from utils import validate_positive_number


class PredictionService(BaseService[PredictionHistory]):
    """CRUD operations for the `prediction_history` table."""

    model = PredictionHistory
    pk_column = "prediction_id"

    def log_prediction(
        self,
        user_id: int,
        ticker_symbol: str,
        model_name: str,
        predicted_price: float,
        prediction_horizon_days: int = 1,
        confidence_score: float | None = None,
    ) -> PredictionHistory:
        """Persist a single model prediction result."""
        validate_positive_number(predicted_price, "predicted_price")
        if prediction_horizon_days <= 0:
            raise ValidationError("prediction_horizon_days must be a positive integer.")
        if confidence_score is not None and not (0 <= confidence_score <= 100):
            raise ValidationError("confidence_score must be between 0 and 100.")

        entry = PredictionHistory(
            user_id=user_id,
            ticker_symbol=ticker_symbol.strip().upper(),
            model_name=model_name.strip(),
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            prediction_horizon_days=prediction_horizon_days,
        )
        created = self.create(entry)
        logger.info(f"Prediction logged: user_id={user_id}, ticker={entry.ticker_symbol}, model={model_name}")
        return created

    def get_predictions_for_ticker(
        self, user_id: int, ticker_symbol: str, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        """List a user's past predictions for a specific ticker, newest first."""
        return self.list(
            filters={"user_id": user_id, "ticker_symbol": ticker_symbol.strip().upper()},
            sort_by="created_at",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )

    def get_user_predictions(self, user_id: int, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """List every prediction ever generated for a user, newest first."""
        return self.list(
            filters={"user_id": user_id}, sort_by="created_at", sort_direction="desc", page=page, page_size=page_size
        )


prediction_service = PredictionService()
