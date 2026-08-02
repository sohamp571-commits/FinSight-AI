"""
machine_learning/model_storage.py

Purpose: Persists trained models to disk (joblib) so a model doesn't
need to be retrained on every single prediction request, and loads
them back for reuse. Storage is keyed by (ticker, model_name, horizon)
since a model trained for a 1-day horizon is not interchangeable with
one trained for a 90-day horizon. No database table is involved here
-- model *artifacts* are files; model *predictions* are what get
stored in the database via prediction_history.py.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import joblib
from sklearn.preprocessing import StandardScaler

from config import config
from custom_exceptions import DatabaseQueryError
from logging_config import logger

MODEL_STORAGE_DIR: Path = config.BASE_DIR / "machine_learning" / "saved_models"
MODEL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FRESHNESS_HOURS = 24  # Retrain if a cached model is older than this.


@dataclass
class StoredModel:
    """Container for a deserialized model artifact and everything needed to use it."""

    model: object
    scaler: StandardScaler
    feature_columns: list[str]
    trained_at: datetime
    model_name: str
    ticker: str
    horizon_days: int


def _artifact_path(ticker: str, model_name: str, horizon_days: int) -> Path:
    """Build a filesystem-safe path for a given (ticker, model, horizon) artifact."""
    safe_ticker = ticker.replace(".", "_").replace("^", "")
    safe_model_name = model_name.replace(" ", "_").lower()
    filename = f"{safe_ticker}__{safe_model_name}__{horizon_days}d.joblib"
    return MODEL_STORAGE_DIR / filename


def save_model(
    ticker: str, model_name: str, horizon_days: int, model: object, scaler: StandardScaler, feature_columns: list[str]
) -> Path:
    """Serialize a trained model + its scaler + feature list to disk."""
    path = _artifact_path(ticker, model_name, horizon_days)
    payload = {
        "model": model,
        "scaler": scaler,
        "feature_columns": feature_columns,
        "trained_at": datetime.utcnow(),
        "model_name": model_name,
        "ticker": ticker,
        "horizon_days": horizon_days,
    }
    try:
        joblib.dump(payload, path)
        logger.info(f"Model artifact saved: {path.name}")
        return path
    except OSError as exc:
        logger.error(f"Failed to save model artifact '{path.name}': {exc}")
        raise DatabaseQueryError(f"Could not save the trained model to disk: {exc}") from exc


def load_model(ticker: str, model_name: str, horizon_days: int) -> StoredModel | None:
    """Load a previously saved model artifact, or None if it doesn't exist or fails to load."""
    path = _artifact_path(ticker, model_name, horizon_days)
    if not path.exists():
        return None

    try:
        payload = joblib.load(path)
        return StoredModel(
            model=payload["model"],
            scaler=payload["scaler"],
            feature_columns=payload["feature_columns"],
            trained_at=payload["trained_at"],
            model_name=payload["model_name"],
            ticker=payload["ticker"],
            horizon_days=payload["horizon_days"],
        )
    except (OSError, KeyError, EOFError) as exc:
        logger.warning(f"Failed to load model artifact '{path.name}', will retrain: {exc}")
        return None


def is_model_fresh(stored_model: StoredModel, freshness_hours: int = MODEL_FRESHNESS_HOURS) -> bool:
    """Return True if a stored model was trained recently enough to reuse without retraining."""
    age = datetime.utcnow() - stored_model.trained_at
    return age < timedelta(hours=freshness_hours)


def delete_model(ticker: str, model_name: str, horizon_days: int) -> bool:
    """Delete a stored model artifact, e.g. to force a retrain. Returns True if a file was removed."""
    path = _artifact_path(ticker, model_name, horizon_days)
    if path.exists():
        path.unlink()
        logger.info(f"Model artifact deleted: {path.name}")
        return True
    return False
