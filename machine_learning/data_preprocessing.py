"""
machine_learning/data_preprocessing.py

Purpose: Cleans and scales the engineered feature matrix before it
reaches a model. Handles the NaN "warm-up" period every rolling/lag
indicator introduces, guards against infinite values from ratio-based
features (e.g. bb_width dividing by a near-zero middle band), and
provides a fitted scaler that `forecasting.py` reuses at prediction
time so training and inference stay on the same scale.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.preprocessing import StandardScaler

from custom_exceptions import DataProcessingError
from logging_config import logger


@dataclass
class PreprocessedData:
    """Container for a cleaned, scaled feature matrix ready for train/test splitting."""

    features: pd.DataFrame
    target: pd.Series
    scaler: StandardScaler
    feature_columns: list[str]


def clean_feature_matrix(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """Replace infinities with NaN, then drop any row with a NaN in a feature or the target column."""
    cleaned = df.copy()
    columns_to_check = feature_columns + (["target"] if "target" in cleaned.columns else [])
    cleaned[columns_to_check] = cleaned[columns_to_check].replace([float("inf"), float("-inf")], pd.NA)
    cleaned = cleaned.dropna(subset=columns_to_check)
    return cleaned


def preprocess_features(df: pd.DataFrame, feature_columns: list[str]) -> PreprocessedData:
    """
    Clean the feature matrix and fit a StandardScaler on the feature
    columns (target column is left unscaled -- regression models
    predict actual price, not a normalized value).

    Raises:
        DataProcessingError: if too few rows remain after cleaning to train on.
    """
    if "target" not in df.columns:
        raise DataProcessingError("Feature matrix is missing the 'target' column -- call add_target_column() first.")

    cleaned = clean_feature_matrix(df, feature_columns)
    if len(cleaned) < 50:
        raise DataProcessingError(
            f"Only {len(cleaned)} usable rows remain after cleaning (indicator warm-up periods "
            f"and the prediction horizon both consume rows); at least 50 are required to train."
        )

    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(cleaned[feature_columns])
    scaled_features = pd.DataFrame(scaled_values, columns=feature_columns, index=cleaned.index)

    logger.info(f"Preprocessed feature matrix: {len(cleaned)} rows, {len(feature_columns)} features.")
    return PreprocessedData(
        features=scaled_features,
        target=cleaned["target"],
        scaler=scaler,
        feature_columns=feature_columns,
    )


def scale_new_observations(raw_features: pd.DataFrame, scaler: StandardScaler, feature_columns: list[str]) -> pd.DataFrame:
    """Apply an already-fitted scaler to new (unseen) feature rows, e.g. for forecasting."""
    aligned = raw_features[feature_columns].replace([float("inf"), float("-inf")], pd.NA)
    if aligned.isna().any().any():
        raise DataProcessingError("Cannot scale observations containing missing/infinite feature values.")
    scaled_values = scaler.transform(aligned)
    return pd.DataFrame(scaled_values, columns=feature_columns, index=raw_features.index)
