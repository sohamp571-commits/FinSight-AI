"""
machine_learning/prediction_dashboard.py

Purpose: The main entry point for the Machine Learning & Stock Price
Prediction module. Lets the user pick a ticker, a model (or several,
for comparison), and a prediction horizon; trains/evaluates/forecasts;
and renders every visualization from visualization.py plus the user's
prediction history (reused from the existing prediction_history table).
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.chart_helpers import CHART_CONFIG
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from logging_config import logger

from machine_learning.dataset_loader import load_training_dataset
from machine_learning.forecasting import SUPPORTED_HORIZONS
from machine_learning.model_manager import get_available_model_names, is_xgboost_available
from machine_learning.prediction_history import estimate_target_date, get_ticker_prediction_history
from machine_learning.prediction_service import compare_models, run_prediction
from machine_learning.visualization import (
    build_actual_vs_predicted_chart,
    build_confidence_gauge,
    build_feature_importance_chart,
    build_future_forecast_chart,
    build_model_comparison_chart,
    build_residual_plot,
    format_evaluation_summary,
)


def _render_controls() -> tuple[str, list[str], str, bool]:
    """Render the query/model/horizon/retrain controls, returning the user's selections."""
    col1, col2 = st.columns([3, 2])
    with col1:
        query = st.text_input(
            "🔍 Company name or ticker symbol",
            placeholder="e.g. Reliance Industries, TCS, INFY.NS, AAPL",
            key="ml_search_query",
        )
    with col2:
        horizon_label = st.selectbox("Prediction Horizon", list(SUPPORTED_HORIZONS.keys()), index=2)

    available_models = get_available_model_names()
    if not is_xgboost_available():
        st.caption("ℹ️ XGBoost is not installed in this environment, so it's omitted from the model list.")

    selected_models = st.multiselect(
        "Model(s) — select one for a full report, or several to compare",
        options=available_models,
        default=[available_models[0]],
        key="ml_selected_models",
    )
    force_retrain = st.checkbox("Force retrain (ignore cached model)", value=False)

    return query, selected_models, horizon_label, force_retrain


def _render_single_model_report(user_id: int, query: str, model_name: str, horizon_label: str, force_retrain: bool) -> None:
    """Render the full report for a single selected model: forecast, evaluation, and every chart."""
    with st.spinner(f"Training/evaluating {model_name} for {horizon_label} horizon..."):
        ticker, result = run_prediction(user_id, query, model_name, horizon_label, force_retrain)

    change_icon = "🟢" if result.predicted_change_pct >= 0 else "🔴"
    st.markdown(f"## {ticker} — {model_name} Forecast")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Price", f"{result.current_price:,.2f}")
    with col2:
        st.metric(
            f"Predicted Price ({result.horizon_days}d)",
            f"{result.predicted_price:,.2f}",
            delta=f"{result.predicted_change_pct:+.2f}%",
        )
    with col3:
        st.metric("Model Quality", result.quality_label)

    st.caption(f"{change_icon} Model {'retrained just now' if result.trained_fresh else 'reused from cache'}.")
    render_divider()

    render_section_header("Future Forecast", icon="🔮")
    raw_df = load_training_dataset(ticker)
    st.plotly_chart(
        build_future_forecast_chart(result, raw_df["Close"].tail(120)),
        use_container_width=True, config=CHART_CONFIG, key="future_forecast_chart",
    )

    eval_tab, actual_tab, residual_tab, importance_tab = st.tabs(
        ["Evaluation Metrics", "Actual vs Predicted", "Residuals", "Feature Importance"]
    )
    with eval_tab:
        summary = format_evaluation_summary(result.evaluation)
        cols = st.columns(len(summary))
        for col, (label, value) in zip(cols, summary.items()):
            col.metric(label, value)
        st.plotly_chart(
            build_confidence_gauge(result.confidence_score, result.quality_label),
            use_container_width=True, config=CHART_CONFIG, key="confidence_gauge",
        )
    with actual_tab:
        st.plotly_chart(build_actual_vs_predicted_chart(result), use_container_width=True, config=CHART_CONFIG, key="actual_vs_predicted")
    with residual_tab:
        st.plotly_chart(build_residual_plot(result), use_container_width=True, config=CHART_CONFIG, key="residual_plot")
    with importance_tab:
        st.plotly_chart(
            build_feature_importance_chart(result.feature_importances),
            use_container_width=True, config=CHART_CONFIG, key="feature_importance",
        )

    render_divider()
    _render_prediction_history(user_id, ticker)


def _render_model_comparison(user_id: int, query: str, model_names: list[str], horizon_label: str) -> None:
    """Render a side-by-side comparison across multiple selected models."""
    with st.spinner(f"Training/evaluating {len(model_names)} models for comparison..."):
        results = compare_models(user_id, query, model_names, horizon_label)

    render_section_header("Model Comparison", icon="⚔️")
    st.plotly_chart(build_model_comparison_chart(results), use_container_width=True, config=CHART_CONFIG, key="model_comparison_chart")

    rows = []
    for name, result in results.items():
        if result is None:
            rows.append({"Model": name, "Predicted Price": "Failed", "R² Score": "N/A", "RMSE": "N/A"})
        else:
            rows.append(
                {
                    "Model": name,
                    "Predicted Price": f"{result.predicted_price:,.2f}",
                    "R² Score": f"{result.evaluation.r2:.4f}",
                    "RMSE": f"{result.evaluation.rmse:,.2f}",
                }
            )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_prediction_history(user_id: int, ticker: str) -> None:
    """Render the user's past predictions for this ticker (reused from the existing prediction_history table)."""
    render_section_header("Prediction History", subtitle=f"Your past predictions for {ticker}", icon="🕓")
    history = get_ticker_prediction_history(user_id, ticker, limit=10)

    if not history:
        st.caption("No previous predictions for this ticker yet.")
        return

    rows = [
        {
            "Predicted On": entry.created_at.strftime("%d %b %Y %H:%M"),
            "Model": entry.model_name,
            "Horizon": f"{entry.prediction_horizon_days}d",
            "Target Date": estimate_target_date(entry.created_at, entry.prediction_horizon_days).strftime("%d %b %Y"),
            "Predicted Price": f"{float(entry.predicted_price):,.2f}",
            "Confidence": f"{float(entry.confidence_score):.1f}%" if entry.confidence_score is not None else "N/A",
        }
        for entry in history
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


@login_required
def render() -> None:
    """Render the full Machine Learning & Stock Price Prediction page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("🤖 ML Stock Price Prediction")
        st.caption(
            "Train and evaluate machine learning models on historical price data to forecast future prices. "
            "Predictions are for educational purposes only and are not financial advice."
        )
        render_divider()

        query, selected_models, horizon_label, force_retrain = _render_controls()

        if not query.strip() or not selected_models:
            st.info("Enter a company/ticker above and select at least one model to generate a prediction.")
            return

        if st.button("🚀 Generate Prediction", type="primary", use_container_width=True):
            if len(selected_models) == 1:
                _render_single_model_report(user_id, query, selected_models[0], horizon_label, force_retrain)
            else:
                _render_model_comparison(user_id, query, selected_models, horizon_label)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in ML prediction dashboard: {exc}")
        st.error(f"Could not generate a prediction: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in ML prediction dashboard: {exc}")
        st.error("An unexpected error occurred while generating the prediction. Please try again.")
