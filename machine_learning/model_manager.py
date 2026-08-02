"""
machine_learning/model_manager.py

Purpose: The model registry for the ML module. Provides a single
`get_model(name)` factory so every other file (prediction_service.py,
forecasting.py, prediction_dashboard.py) refers to models by a
consistent string name rather than importing sklearn classes directly.
XGBoost is imported defensively -- if it isn't installed in a given
environment, it's simply omitted from the registry rather than
crashing the whole module (per the Phase 7 instruction: "XGBoost (if
installed)").
"""

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from custom_exceptions import ValidationError
from logging_config import logger

try:
    from xgboost import XGBRegressor

    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False
    logger.warning("xgboost is not installed; 'XGBoost' will be unavailable in the model registry.")

RANDOM_STATE = 42


def _build_registry() -> dict[str, object]:
    """Build the name -> unfitted estimator registry. Called once at import time."""
    registry: dict[str, object] = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=8, random_state=RANDOM_STATE, n_jobs=-1),
        "Decision Tree": DecisionTreeRegressor(max_depth=8, random_state=RANDOM_STATE),
        "Support Vector Regression": SVR(kernel="rbf", C=100, gamma="scale", epsilon=0.1),
        "K-Nearest Neighbors": KNeighborsRegressor(n_neighbors=5, weights="distance"),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=150, max_depth=4, random_state=RANDOM_STATE),
    }

    if _XGBOOST_AVAILABLE:
        registry["XGBoost"] = XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05, random_state=RANDOM_STATE, n_jobs=-1
        )

    # Voting Regressor: averages predictions from three diverse, fast base
    # models (linear, tree-ensemble, and instance-based) for a more stable
    # consensus estimate than any single model alone.
    voting_estimators = [
        ("linear", LinearRegression()),
        ("random_forest", RandomForestRegressor(n_estimators=150, max_depth=8, random_state=RANDOM_STATE, n_jobs=-1)),
        ("knn", KNeighborsRegressor(n_neighbors=5, weights="distance")),
    ]
    registry["Voting Regressor"] = VotingRegressor(estimators=voting_estimators)

    return registry


_MODEL_REGISTRY: dict[str, object] = _build_registry()


def get_available_model_names() -> list[str]:
    """Return every model name currently available (reflects whether XGBoost is installed)."""
    return list(_MODEL_REGISTRY.keys())


def get_model(name: str):
    """
    Return a fresh, unfitted clone of the requested model.

    Raises:
        ValidationError: if `name` isn't a registered model.
    """
    if name not in _MODEL_REGISTRY:
        raise ValidationError(
            f"Unknown model '{name}'. Available models: {', '.join(get_available_model_names())}"
        )
    from sklearn.base import clone

    return clone(_MODEL_REGISTRY[name])


def is_xgboost_available() -> bool:
    """Whether the XGBoost model is available in this environment."""
    return _XGBOOST_AVAILABLE
