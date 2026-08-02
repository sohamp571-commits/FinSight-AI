"""
machine_learning/cross_validation.py

Purpose: Runs time-series-aware cross-validation using scikit-learn's
`TimeSeriesSplit` (expanding-window folds that always train on the
past and validate on the future) rather than standard k-fold, which
would leak future information into training exactly like a random
train/test split would. Used to sanity-check a model's stability
across multiple periods before it's trusted for forecasting.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import TimeSeriesSplit

from custom_exceptions import DataProcessingError
from logging_config import logger
from machine_learning.evaluation_metrics import evaluate_predictions

DEFAULT_N_SPLITS = 5


@dataclass
class CrossValidationResult:
    """Container for time-series cross-validation results across all folds."""

    fold_r2_scores: list[float]
    fold_rmse_scores: list[float]
    mean_r2: float
    mean_rmse: float
    std_r2: float


def run_time_series_cross_validation(
    model, features: pd.DataFrame, target: pd.Series, n_splits: int = DEFAULT_N_SPLITS
) -> CrossValidationResult:
    """
    Run expanding-window time-series cross-validation for a given
    (unfitted) model and return per-fold and aggregate R2/RMSE scores.

    Raises:
        DataProcessingError: if there isn't enough data for the requested number of splits.
    """
    minimum_required_rows = (n_splits + 1) * 10
    if len(features) < minimum_required_rows:
        raise DataProcessingError(
            f"Not enough data ({len(features)} rows) for {n_splits}-fold time-series "
            f"cross-validation; at least {minimum_required_rows} rows are required."
        )

    splitter = TimeSeriesSplit(n_splits=n_splits)
    fold_r2_scores: list[float] = []
    fold_rmse_scores: list[float] = []

    for fold_index, (train_idx, val_idx) in enumerate(splitter.split(features), start=1):
        x_train, x_val = features.iloc[train_idx], features.iloc[val_idx]
        y_train, y_val = target.iloc[train_idx], target.iloc[val_idx]

        fold_model = clone(model)
        fold_model.fit(x_train, y_train)
        predictions = fold_model.predict(x_val)

        result = evaluate_predictions(y_val, predictions)
        fold_r2_scores.append(result.r2)
        fold_rmse_scores.append(result.rmse)
        logger.info(f"CV fold {fold_index}/{n_splits}: R2={result.r2:.3f}, RMSE={result.rmse:.3f}")

    return CrossValidationResult(
        fold_r2_scores=fold_r2_scores,
        fold_rmse_scores=fold_rmse_scores,
        mean_r2=float(np.mean(fold_r2_scores)),
        mean_rmse=float(np.mean(fold_rmse_scores)),
        std_r2=float(np.std(fold_r2_scores)),
    )
