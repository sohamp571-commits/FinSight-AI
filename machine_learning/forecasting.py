"""
machine_learning/forecasting.py

Purpose: The core ML orchestration layer. Ties together
dataset_loader -> feature_engineering -> data_preprocessing ->
train_test_split -> model_manager -> evaluation_metrics -> model_storage
into one `forecast_price()` call that either reuses a fresh cached
model or trains a new one, evaluates it honestly on held-out data, and
produces a single-point future price forecast for the requested
horizon.

Design note on methodology: FinSight AI trains one model *per horizon*
(target = closing price N trading days ahead) rather than recursively
chaining a 1-day-ahead model N times. Direct multi-step forecasting is
the standard, more numerically stable approach for medium/long
horizons (7-90 days) because it avoids compounding a small daily error
across dozens of recursive steps. The "forecast path" drawn on the
chart is therefore an explicit, labeled linear interpolation between
today's price and the model's single-horizon estimate -- it visualizes
the target, it does not claim day-by-day predictive precision.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from custom_exceptions import DataProcessingError
from logging_config import logger
from machine_learning.data_preprocessing import PreprocessedData, preprocess_features, scale_new_observations
from machine_learning.dataset_loader import load_training_dataset
from machine_learning.evaluation_metrics import (
    EvaluationResult,
    classify_model_quality,
    confidence_score_from_evaluation,
    evaluate_predictions,
)
from machine_learning.feature_engineering import add_target_column, build_feature_matrix, get_feature_columns
from machine_learning.model_manager import get_model
from machine_learning.model_storage import StoredModel, is_model_fresh, load_model, save_model
from machine_learning.train_test_split import SplitData, chronological_split

SUPPORTED_HORIZONS: dict[str, int] = {
    "1 Day": 1,
    "3 Day": 3,
    "5 Day": 5,
    "7 Day": 7,
    "15 Day": 15,
    "30 Day": 30,
    "90 Day": 90,
}


@dataclass
class ForecastResult:
    """Everything the dashboard needs to display one forecast."""

    ticker: str
    model_name: str
    horizon_days: int
    current_price: float
    predicted_price: float
    predicted_change_pct: float
    evaluation: EvaluationResult
    quality_label: str
    confidence_score: float
    forecast_path: list[tuple[datetime, float]]
    trained_fresh: bool
    x_test_dates: pd.DatetimeIndex
    y_test: pd.Series
    y_test_predictions: pd.Series
    feature_importances: dict[str, float] | None


def _prepare_horizon_dataset(ticker: str, horizon_days: int) -> tuple[pd.DataFrame, list[str]]:
    """Load raw data, engineer features, and attach the target column for this horizon."""
    raw_df = load_training_dataset(ticker)
    engineered_df = build_feature_matrix(raw_df)
    engineered_df = add_target_column(engineered_df, horizon_days)
    feature_columns = get_feature_columns(engineered_df)
    feature_columns = [col for col in feature_columns if col != "target"]
    return engineered_df, feature_columns


def _extract_feature_importances(model, feature_columns: list[str]) -> dict[str, float] | None:
    """Extract feature importances if the underlying model exposes them (tree-based models)."""
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return None
    return dict(sorted(zip(feature_columns, importances), key=lambda pair: pair[1], reverse=True))


def train_model_for_horizon(ticker: str, model_name: str, horizon_days: int) -> tuple[StoredModel, SplitData, EvaluationResult, dict[str, float] | None]:
    """
    Train a fresh model for the given (ticker, model_name, horizon_days),
    evaluate it on a chronological hold-out set, and persist it to disk.
    """
    engineered_df, feature_columns = _prepare_horizon_dataset(ticker, horizon_days)
    preprocessed: PreprocessedData = preprocess_features(engineered_df, feature_columns)
    split: SplitData = chronological_split(preprocessed)

    model = get_model(model_name)
    model.fit(split.x_train, split.y_train)
    predictions = model.predict(split.x_test)
    evaluation = evaluate_predictions(split.y_test, predictions)

    save_model(ticker, model_name, horizon_days, model, preprocessed.scaler, feature_columns)
    logger.info(
        f"Trained '{model_name}' for {ticker} ({horizon_days}d horizon): "
        f"R2={evaluation.r2:.3f}, RMSE={evaluation.rmse:.3f}"
    )

    stored = StoredModel(
        model=model,
        scaler=preprocessed.scaler,
        feature_columns=feature_columns,
        trained_at=datetime.utcnow(),
        model_name=model_name,
        ticker=ticker,
        horizon_days=horizon_days,
    )
    importances = _extract_feature_importances(model, feature_columns)
    return stored, split, evaluation, importances


def forecast_price(ticker: str, model_name: str, horizon_label: str, force_retrain: bool = False) -> ForecastResult:
    """
    Produce a full forecast for a ticker: trains (or reuses a fresh
    cached model for) the requested model/horizon, evaluates it, and
    returns a single-point future price estimate plus everything
    needed to visualize it.

    Raises:
        DataProcessingError: if the horizon label is invalid.
    """
    if horizon_label not in SUPPORTED_HORIZONS:
        raise DataProcessingError(
            f"Unsupported prediction horizon '{horizon_label}'. Choose from: {', '.join(SUPPORTED_HORIZONS)}"
        )
    horizon_days = SUPPORTED_HORIZONS[horizon_label]

    stored = None if force_retrain else load_model(ticker, model_name, horizon_days)
    trained_fresh = False

    if stored is not None and is_model_fresh(stored):
        engineered_df, feature_columns = _prepare_horizon_dataset(ticker, horizon_days)
        preprocessed = preprocess_features(engineered_df, feature_columns)
        split = chronological_split(preprocessed)
        predictions = stored.model.predict(split.x_test)
        evaluation = evaluate_predictions(split.y_test, predictions)
        model = stored.model
        scaler = stored.scaler
        feature_columns = stored.feature_columns
        importances = _extract_feature_importances(model, feature_columns)
    else:
        stored, split, evaluation, importances = train_model_for_horizon(ticker, model_name, horizon_days)
        model, scaler, feature_columns = stored.model, stored.scaler, stored.feature_columns
        trained_fresh = True
        predictions = model.predict(split.x_test)

    # Forecast the single future point using the most recent available feature row
    # (the last row of the raw, unshifted engineered matrix -- the target for this
    # row is unknown, which is exactly what we're predicting).
    raw_df = load_training_dataset(ticker)
    engineered_df = build_feature_matrix(raw_df)
    latest_features = engineered_df[feature_columns].iloc[[-1]].replace([float("inf"), float("-inf")], pd.NA)
    if latest_features.isna().any(axis=None):
        raise DataProcessingError(
            f"The most recent trading data for {ticker} is incomplete for one or more indicators; "
            f"cannot generate a forecast right now."
        )

    scaled_latest = scale_new_observations(latest_features, scaler, feature_columns)
    predicted_price = float(model.predict(scaled_latest)[0])
    current_price = float(raw_df["Close"].iloc[-1])
    predicted_change_pct = ((predicted_price - current_price) / current_price) * 100 if current_price else 0.0

    target_date = raw_df.index[-1] + timedelta(days=horizon_days)
    forecast_path = [(raw_df.index[-1].to_pydatetime(), current_price), (target_date.to_pydatetime() if hasattr(target_date, "to_pydatetime") else target_date, predicted_price)]

    return ForecastResult(
        ticker=ticker,
        model_name=model_name,
        horizon_days=horizon_days,
        current_price=current_price,
        predicted_price=predicted_price,
        predicted_change_pct=predicted_change_pct,
        evaluation=evaluation,
        quality_label=classify_model_quality(evaluation),
        confidence_score=confidence_score_from_evaluation(evaluation),
        forecast_path=forecast_path,
        trained_fresh=trained_fresh,
        x_test_dates=split.x_test.index,
        y_test=split.y_test,
        y_test_predictions=pd.Series(predictions, index=split.y_test.index),
        feature_importances=importances,
    )
