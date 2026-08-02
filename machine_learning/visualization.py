"""
machine_learning/visualization.py

Purpose: Every Plotly chart builder specific to the ML module --
Actual vs Predicted, Future Forecast, Residual Plot, Feature
Importance, Prediction Confidence, and Model Comparison. Reuses
`dashboard.chart_helpers.apply_dark_theme` and the shared color
palette rather than re-styling each figure from scratch.
"""

import pandas as pd
import plotly.graph_objects as go

from dashboard.chart_helpers import COLOR_ACCENT, COLOR_NEGATIVE, COLOR_NEUTRAL, COLOR_POSITIVE, apply_dark_theme
from machine_learning.evaluation_metrics import EvaluationResult
from machine_learning.forecasting import ForecastResult


def build_actual_vs_predicted_chart(result: ForecastResult) -> go.Figure:
    """Build the Actual vs Predicted chart for the held-out test set."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=result.x_test_dates, y=result.y_test, mode="lines", line=dict(color=COLOR_NEUTRAL, width=2), name="Actual")
    )
    fig.add_trace(
        go.Scatter(x=result.x_test_dates, y=result.y_test_predictions, mode="lines", line=dict(color=COLOR_ACCENT, width=2, dash="dot"), name="Predicted")
    )
    fig.update_layout(title=f"Actual vs Predicted — {result.model_name} ({result.horizon_days}-Day Horizon)")
    return apply_dark_theme(fig, height=360, show_legend=True)


def build_future_forecast_chart(result: ForecastResult, recent_history: pd.Series) -> go.Figure:
    """
    Build the Future Forecast chart: recent actual closing price plus
    the model's single-point forecast, connected by a clearly-dashed
    line (see forecasting.py's module docstring for why this is a
    labeled interpolation rather than a claimed daily prediction path).
    """
    forecast_dates = [point[0] for point in result.forecast_path]
    forecast_prices = [point[1] for point in result.forecast_path]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=recent_history.index, y=recent_history, mode="lines", line=dict(color=COLOR_NEUTRAL, width=2), name="Historical Close")
    )
    fig.add_trace(
        go.Scatter(
            x=forecast_dates, y=forecast_prices, mode="lines+markers",
            line=dict(color=COLOR_ACCENT, width=2, dash="dash"),
            marker=dict(size=[6, 12], color=[COLOR_ACCENT, COLOR_POSITIVE if result.predicted_change_pct >= 0 else COLOR_NEGATIVE]),
            name=f"Forecast (+{result.horizon_days}d)",
        )
    )
    fig.update_layout(title=f"{result.ticker} — Future Forecast ({result.horizon_days}-Day)")
    return apply_dark_theme(fig, height=380, show_legend=True)


def build_residual_plot(result: ForecastResult) -> go.Figure:
    """Build a residual plot (actual - predicted) over the test period, to check for systematic bias."""
    residuals = result.y_test - result.y_test_predictions
    colors = [COLOR_POSITIVE if r >= 0 else COLOR_NEGATIVE for r in residuals]

    fig = go.Figure(go.Bar(x=result.x_test_dates, y=residuals, marker_color=colors, name="Residual"))
    fig.add_hline(y=0, line_color="rgba(148,163,184,0.5)")
    fig.update_layout(title="Residual Plot (Actual − Predicted)")
    return apply_dark_theme(fig, height=280)


def build_feature_importance_chart(feature_importances: dict[str, float] | None, top_n: int = 12) -> go.Figure:
    """Build a horizontal bar chart of the top-N most important features (if the model supports it)."""
    fig = go.Figure()
    if not feature_importances:
        fig.add_annotation(text="Feature importance is not available for this model.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=300)

    top_features = list(feature_importances.items())[:top_n]
    names = [name for name, _ in reversed(top_features)]
    values = [value for _, value in reversed(top_features)]

    fig.add_trace(go.Bar(x=values, y=names, orientation="h", marker_color=COLOR_ACCENT))
    fig.update_layout(title="Feature Importance")
    return apply_dark_theme(fig, height=max(300, 24 * len(top_features)))


def build_confidence_gauge(confidence_score: float, quality_label: str) -> go.Figure:
    """Build a gauge chart showing the model's confidence score (0-100, derived from R2)."""
    color = COLOR_POSITIVE if confidence_score >= 65 else ("#F59E0B" if confidence_score >= 40 else COLOR_NEGATIVE)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence_score,
            number={"suffix": "%"},
            title={"text": f"Prediction Confidence — {quality_label}"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 40], "color": "rgba(239,68,68,0.15)"},
                    {"range": [40, 65], "color": "rgba(245,158,11,0.15)"},
                    {"range": [65, 100], "color": "rgba(34,197,94,0.15)"},
                ],
            },
        )
    )
    return apply_dark_theme(fig, height=260)


def build_model_comparison_chart(results: dict[str, "ForecastResult | None"]) -> go.Figure:
    """Build a grouped bar chart comparing predicted price and R2 score across multiple models."""
    valid_results = {name: r for name, r in results.items() if r is not None}
    if not valid_results:
        fig = go.Figure()
        fig.add_annotation(text="No successful model results to compare.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=320)

    names = list(valid_results.keys())
    predicted_prices = [r.predicted_price for r in valid_results.values()]
    r2_scores = [max(0.0, r.evaluation.r2) * 100 for r in valid_results.values()]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=predicted_prices, name="Predicted Price", marker_color=COLOR_ACCENT, yaxis="y1"))
    fig.add_trace(
        go.Scatter(x=names, y=r2_scores, name="R² Score (%)", mode="lines+markers", marker_color="#F59E0B", yaxis="y2")
    )
    fig.update_layout(
        title="Model Comparison",
        yaxis=dict(title="Predicted Price"),
        yaxis2=dict(title="R² Score (%)", overlaying="y", side="right", range=[0, 100]),
    )
    return apply_dark_theme(fig, height=380, show_legend=True)


def format_evaluation_summary(evaluation: EvaluationResult) -> dict[str, str]:
    """Format an EvaluationResult into display-ready strings for a metrics grid."""
    return {
        "MAE": f"{evaluation.mae:,.2f}",
        "MSE": f"{evaluation.mse:,.2f}",
        "RMSE": f"{evaluation.rmse:,.2f}",
        "MAPE": f"{evaluation.mape:.2f}%" if evaluation.mape == evaluation.mape else "N/A",  # NaN check
        "R² Score": f"{evaluation.r2:.4f}" if evaluation.r2 == evaluation.r2 else "N/A",
    }
