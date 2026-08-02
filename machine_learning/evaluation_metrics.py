"""
machine_learning/evaluation_metrics.py

Purpose: Computes the standard regression evaluation metrics (MAE,
MSE, RMSE, MAPE, R2) for a trained model's predictions against the
held-out test set, plus a plain-English quality classification used
by prediction_dashboard.py's confidence display.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass
class EvaluationResult:
    """Container for a model's evaluation metrics on a held-out test set."""

    mae: float
    mse: float
    rmse: float
    mape: float
    r2: float


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Mean Absolute Percentage Error, expressed as a percentage.
    Rows where the true value is exactly zero are excluded to avoid
    division by zero (stock prices are never exactly zero in practice,
    but this guards against degenerate test data).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_predictions(y_true, y_pred) -> EvaluationResult:
    """Compute the full evaluation metric suite for a set of predictions."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    mape = calculate_mape(y_true, y_pred)
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) >= 2 else float("nan")

    return EvaluationResult(mae=mae, mse=mse, rmse=rmse, mape=mape, r2=r2)


def classify_model_quality(evaluation: EvaluationResult) -> str:
    """
    Translate an R2 score into a plain-English quality label. R2 is
    used as the headline metric since it's scale-independent (unlike
    MAE/RMSE, which depend on the ticker's absolute price level).
    """
    if np.isnan(evaluation.r2):
        return "Unknown"
    if evaluation.r2 >= 0.85:
        return "Excellent Fit"
    if evaluation.r2 >= 0.65:
        return "Good Fit"
    if evaluation.r2 >= 0.40:
        return "Moderate Fit"
    if evaluation.r2 >= 0:
        return "Weak Fit"
    return "Poor Fit (worse than predicting the average)"


def confidence_score_from_evaluation(evaluation: EvaluationResult) -> float:
    """
    Derive a 0-100 confidence score from R2 for storage in
    `prediction_history.confidence_score` (a DECIMAL(5,2) column).
    Clamped to [0, 100] since R2 can be negative for a poorly-fit model.
    """
    if np.isnan(evaluation.r2):
        return 0.0
    return round(max(0.0, min(1.0, evaluation.r2)) * 100, 2)
