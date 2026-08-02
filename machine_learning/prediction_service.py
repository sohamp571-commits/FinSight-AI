"""
machine_learning/prediction_service.py

Purpose: The application-level service layer for ML predictions --
sits above `forecasting.py` (pure ML orchestration) and adds the
concerns a real request needs: resolving/validating the ticker (reused
from stock_search), running the forecast, persisting the result to
`prediction_history` (reused from database/prediction_service.py via
machine_learning/prediction_history.py), and writing an audit log
entry. `prediction_dashboard.py` calls this module, not
`forecasting.py`, directly.
"""

from custom_exceptions import FinSightBaseException, ValidationError
from database.audit_service import audit_service
from logging_config import logger
from machine_learning.forecasting import ForecastResult, SUPPORTED_HORIZONS, forecast_price
from machine_learning.model_manager import get_available_model_names
from machine_learning.prediction_history import record_prediction
from stock_search.search_service import resolve_ticker, validate_ticker_exists


def run_prediction(
    user_id: int, query: str, model_name: str, horizon_label: str, force_retrain: bool = False
) -> tuple[str, ForecastResult]:
    """
    Full end-to-end prediction request: resolve the ticker, validate
    model/horizon choices, run the forecast, log it to prediction
    history and the audit trail.

    Returns:
        (resolved_ticker, ForecastResult)

    Raises:
        ValidationError: if the ticker/model/horizon are invalid.
        FinSightBaseException subclasses: on data/training failures (propagated from forecasting.py).
    """
    ticker = resolve_ticker(query)
    if not validate_ticker_exists(ticker):
        raise ValidationError(f"'{query}' could not be resolved to a valid, actively-traded ticker.")

    if model_name not in get_available_model_names():
        raise ValidationError(f"'{model_name}' is not an available model.")
    if horizon_label not in SUPPORTED_HORIZONS:
        raise ValidationError(f"'{horizon_label}' is not a supported prediction horizon.")

    try:
        result = forecast_price(ticker, model_name, horizon_label, force_retrain=force_retrain)
    except FinSightBaseException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface unexpected ML/sklearn errors as a domain exception
        logger.exception(f"Unexpected error while forecasting {ticker} with {model_name}: {exc}")
        raise ValidationError(f"Could not generate a prediction for {ticker} right now: {exc}") from exc

    record_prediction(
        user_id=user_id,
        ticker=ticker,
        model_name=model_name,
        predicted_price=result.predicted_price,
        confidence_score=result.confidence_score,
        horizon_days=result.horizon_days,
    )

    audit_service.log_action(
        action="ML_PREDICTION_GENERATED",
        user_id=user_id,
        entity_type="ticker",
        details=f"{ticker} | {model_name} | {horizon_label} | predicted={result.predicted_price:.2f}",
    )

    return ticker, result


def compare_models(
    user_id: int, query: str, model_names: list[str], horizon_label: str
) -> dict[str, ForecastResult | None]:
    """
    Run the same forecast across multiple models for side-by-side
    comparison. A single model's failure doesn't abort the others --
    it's recorded as None so the UI can show a per-model error state.
    """
    ticker = resolve_ticker(query)
    if not validate_ticker_exists(ticker):
        raise ValidationError(f"'{query}' could not be resolved to a valid, actively-traded ticker.")

    results: dict[str, ForecastResult | None] = {}
    for model_name in model_names:
        try:
            _, result = run_prediction(user_id, ticker, model_name, horizon_label)
            results[model_name] = result
        except FinSightBaseException as exc:
            logger.error(f"Model comparison: '{model_name}' failed for {ticker}: {exc}")
            results[model_name] = None

    return results
