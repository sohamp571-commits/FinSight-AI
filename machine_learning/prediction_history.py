"""
machine_learning/prediction_history.py

Purpose: The ML module's only touchpoint with the database -- and it
deliberately does *not* define a new service or table. Per the Phase 7
instruction to reuse the existing `prediction_history` table, this
file is a thin, ML-module-local wrapper around the already-complete
`database.prediction_service.prediction_service` (Phase 3), adding
only the horizon-to-days bookkeeping and result formatting the
dashboard needs.
"""

from datetime import datetime, timedelta

from database.models import PredictionHistory
from database.prediction_service import prediction_service
from logging_config import logger


def record_prediction(
    user_id: int,
    ticker: str,
    model_name: str,
    predicted_price: float,
    confidence_score: float,
    horizon_days: int,
) -> PredictionHistory:
    """
    Persist a single prediction result to the existing `prediction_history`
    table via database.prediction_service (no schema changes).
    """
    entry = prediction_service.log_prediction(
        user_id=user_id,
        ticker_symbol=ticker,
        model_name=model_name,
        predicted_price=predicted_price,
        prediction_horizon_days=horizon_days,
        confidence_score=confidence_score,
    )
    logger.info(
        f"Prediction recorded: user_id={user_id}, ticker={ticker}, model={model_name}, "
        f"horizon={horizon_days}d, price={predicted_price:.2f}"
    )
    return entry


def get_ticker_prediction_history(user_id: int, ticker: str, limit: int = 10) -> list[PredictionHistory]:
    """Fetch a user's past predictions for a specific ticker, newest first."""
    result = prediction_service.get_predictions_for_ticker(user_id, ticker, page_size=limit)
    return result["items"]


def get_all_prediction_history(user_id: int, limit: int = 25) -> list[PredictionHistory]:
    """Fetch every prediction a user has ever generated, across all tickers, newest first."""
    result = prediction_service.get_user_predictions(user_id, page_size=limit)
    return result["items"]


def estimate_target_date(prediction_date: datetime, horizon_days: int) -> datetime:
    """
    Estimate the calendar date a prediction targets. Uses a simple
    calendar-day offset (not a trading-day calendar) for display
    purposes only -- the model itself operates in trading-day steps.
    """
    return prediction_date + timedelta(days=horizon_days)
