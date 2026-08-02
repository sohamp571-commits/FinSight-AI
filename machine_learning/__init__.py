"""
machine_learning package

Phase 7 — Machine Learning & Stock Price Prediction for FinSight AI.

Sub-modules:
    dataset_loader.py        - loads training data (reuses analytics.indicator_service)
    feature_engineering.py    - builds the full feature set (reuses analytics/ indicators)
    data_preprocessing.py      - cleaning + scaling
    train_test_split.py         - chronological (non-shuffled) train/test split
    model_manager.py             - model registry (Linear/RF/DT/SVR/KNN/XGBoost/GB/Voting)
    evaluation_metrics.py         - MAE / MSE / RMSE / MAPE / R2
    cross_validation.py            - TimeSeriesSplit cross-validation
    model_storage.py                - joblib persistence of trained models
    forecasting.py                   - orchestrates train/load -> evaluate -> forecast
    prediction_history.py             - thin wrapper over the existing prediction_history table
    prediction_service.py              - application-level service (auth/audit integration)
    visualization.py                    - every ML-specific Plotly chart
    prediction_dashboard.py              - main controller (entry point: prediction_dashboard.render)
"""

from machine_learning.prediction_dashboard import render

__all__ = ["render"]
