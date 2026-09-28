"""
statistics/statistical_dashboard.py

Purpose: The main entry point for the Statistical Analysis module
(Part 3 of the brief). Follows the exact page pattern already used by
`analytics/technical_analysis.py`: a `@login_required` `render()`
function, FinSight AI's shared dashboard CSS/section-header helpers,
ticker resolution via `stock_search.search_service`, and an audit-log
entry per test run. This file only renders -- all statistics live in
`statistics/hypothesis_tests.py` (T-Test / Chi-Square) and
`statistics/descriptive_statistics.py` (Descriptive Statistics tab),
all data shaping in `statistics/data_preparation.py`.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import DataProcessingError, FinSightBaseException, ValidationError
from dashboard.chart_helpers import (
    CHART_CONFIG,
    COLOR_ACCENT,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    apply_dark_theme,
    build_return_box_plot,
    build_return_histogram,
)
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from database.audit_service import audit_service
from logging_config import logger
from stock_search.historical_data import get_historical_data
from stock_search.search_service import resolve_ticker, validate_ticker_exists

from statistics.data_preparation import (
    get_bullish_bearish_returns,
    get_daily_returns,
    get_rsi_signal_vs_next_day_movement,
)
from statistics.descriptive_statistics import (
    calculate_percentiles,
    calculate_price_statistics,
    calculate_quartiles,
    calculate_return_statistics,
    calculate_volatility,
    describe_kurtosis,
    describe_skewness,
    detect_return_outliers,
)
from statistics.hypothesis_tests import perform_chi_square_test, perform_t_test

PERIOD_OPTIONS: dict[str, str] = {
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "3 Years": "3y",
    "5 Years": "5y",
}


def _safe_audit_log(**kwargs) -> None:
    """
    Best-effort audit logging for a completed test run.

    `database.audit_service.AuditService.log_action` already swallows
    `DatabaseQueryError`, but a lost DB connection surfaces one level
    lower as `DatabaseConnectionError` (raised by
    `database.connection.DatabaseConnection.get_session`), which is
    *not* caught there. An audit-log hiccup must never take down a
    statistical result the user is actively looking at, so this page
    catches that (and anything else) defensively rather than letting
    it propagate.
    """
    try:
        audit_service.log_action(**kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Audit logging failed for statistical analysis (non-fatal): {exc}")


def _resolve_and_validate(query: str) -> str | None:
    """Resolve free-text input to a ticker and confirm it's real, mirroring technical_analysis.py."""
    if not query.strip():
        return None
    ticker = resolve_ticker(query)
    if not validate_ticker_exists(ticker):
        st.error(f"'{query}' could not be resolved to a valid, actively-traded ticker.")
        return None
    return ticker


def _build_group_comparison_chart(result: dict) -> go.Figure:
    """Box plot comparing the two T-test groups' distributions -- easy to read in a viva."""
    fig = go.Figure()
    fig.add_trace(go.Box(y=result["series_a"], name=result["group_a_label"], marker_color=COLOR_ACCENT))
    fig.add_trace(go.Box(y=result["series_b"], name=result["group_b_label"], marker_color=COLOR_NEGATIVE))
    fig.update_layout(title=f"Distribution of {result['metric_name']}s", yaxis_title=result["metric_name"].title())
    return apply_dark_theme(fig, height=360, show_legend=True)


def _build_contingency_chart(result: dict) -> go.Figure:
    """Grouped bar chart of observed counts -- a simple, explainable view of the contingency table."""
    observed: pd.DataFrame = result["observed"]
    fig = go.Figure()
    colors = [COLOR_POSITIVE, COLOR_NEGATIVE, COLOR_ACCENT, "#F59E0B"]
    for i, column in enumerate(observed.columns):
        fig.add_trace(go.Bar(x=observed.index.astype(str), y=observed[column], name=str(column), marker_color=colors[i % len(colors)]))
    fig.update_layout(
        barmode="group",
        title=f"{result['variable_a_label']} vs {result['variable_b_label']} (Observed Counts)",
        xaxis_title=result["variable_a_label"],
        yaxis_title="Count",
    )
    return apply_dark_theme(fig, height=360, show_legend=True)


def _render_t_test_result(result: dict) -> None:
    """Render every field Part 3 of the brief requires for the T-test section."""
    st.markdown(f"**Groups compared:** {result['group_a_label']} vs {result['group_b_label']}")
    st.caption(
        f"H0: {result['null_hypothesis']}  \n"
        f"H1: {result['alternative_hypothesis']}"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(f"Sample size — {result['group_a_label']}", result["n_a"])
    with col2:
        st.metric(f"Sample size — {result['group_b_label']}", result["n_b"])
    with col3:
        st.metric(f"Mean — {result['group_a_label']}", f"{result['mean_a']:.4%}")
    with col4:
        st.metric(f"Mean — {result['group_b_label']}", f"{result['mean_b']:.4%}")

    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("T-statistic", f"{result['t_statistic']:.4f}")
    with col6:
        st.metric("p-value", f"{result['p_value']:.4f}")
    with col7:
        st.metric("Significance level (α)", result["alpha"])

    st.caption(
        f"Test used: **{result['test_name']}** — chosen automatically after checking equal variance with "
        f"Levene's test (statistic={result['levene_stat']:.4f}, p={result['levene_p_value']:.4f})."
    )

    result_color = "🟢" if result["reject_null"] else "🟡"
    st.markdown(f"### {result_color} Result: {result['decision']}")
    st.info(result["interpretation"])

    st.plotly_chart(_build_group_comparison_chart(result), use_container_width=True, config=CHART_CONFIG, key="ttest_chart")


def _render_chi_square_result(result: dict) -> None:
    """Render every field Part 3 of the brief requires for the Chi-square section."""
    st.markdown(f"**Variables tested:** {result['variable_a_label']} vs {result['variable_b_label']}")
    st.caption(
        f"H0: {result['null_hypothesis']}  \n"
        f"H1: {result['alternative_hypothesis']}"
    )

    st.markdown("##### Contingency Table — Observed Frequencies")
    st.dataframe(result["observed"], use_container_width=True)

    with st.expander("Expected Frequencies (under H0)"):
        st.dataframe(result["expected"].round(2), use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Chi-square statistic", f"{result['chi2_statistic']:.4f}")
    with col2:
        st.metric("Degrees of freedom", result["degrees_of_freedom"])
    with col3:
        st.metric("p-value", f"{result['p_value']:.4f}")
    with col4:
        st.metric("Significance level (α)", result["alpha"])

    if result["low_expected_frequency_warning"]:
        st.warning(
            "More than 20% of expected cell frequencies are below 5 — the Chi-square approximation is less "
            "reliable here. Try a longer time period for a more robust result."
        )

    result_color = "🟢" if result["reject_null"] else "🟡"
    st.markdown(f"### {result_color} Result: {result['decision']}")
    st.info(result["interpretation"])

    st.plotly_chart(_build_contingency_chart(result), use_container_width=True, config=CHART_CONFIG, key="chisquare_chart")


def _render_descriptive_statistics_result(ticker: str, history: pd.DataFrame, returns: pd.Series) -> None:
    """Render every section of the Descriptive Statistics tab for an already-fetched ticker."""
    st.markdown(f"**Stock:** {ticker}  |  **Observations:** {len(returns)} daily return(s)")

    # ---- Price Statistics ----
    render_section_header("Price Statistics", subtitle="Open / High / Low / Close / Volume", icon="💰")
    price_stats = calculate_price_statistics(history, ticker)
    st.dataframe(price_stats.style.format("{:,.2f}"), use_container_width=True)
    render_divider()

    # ---- Return Statistics ----
    render_section_header("Return Statistics", subtitle="Descriptive statistics of daily returns", icon="📈")
    return_stats = calculate_return_statistics(returns, ticker)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Mean Return", f"{return_stats['mean']:.4%}")
    with col2:
        st.metric("Median Return", f"{return_stats['median']:.4%}")
    with col3:
        st.metric("Minimum Return", f"{return_stats['min']:.4%}")
    with col4:
        st.metric("Maximum Return", f"{return_stats['max']:.4%}")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Range", f"{return_stats['range']:.4%}")
    with col6:
        st.metric("Standard Deviation", f"{return_stats['std_dev']:.4%}")
    with col7:
        st.metric("Skewness", f"{return_stats['skewness']:.4f}")
    with col8:
        st.metric("Kurtosis", f"{return_stats['kurtosis']:.4f}")
    st.caption(f"Variance: {return_stats['variance']:.6f}")
    render_divider()

    # ---- Quartiles & Percentiles ----
    render_section_header("Quartiles & Percentiles", subtitle="Measures of location", icon="📊")
    col_q, col_p = st.columns(2)
    with col_q:
        st.markdown("**Quartiles**")
        quartiles = calculate_quartiles(returns, ticker)
        st.dataframe(
            pd.DataFrame({"Daily Return": quartiles}).style.format("{:.4%}"), use_container_width=True
        )
    with col_p:
        st.markdown("**Percentiles**")
        percentiles = calculate_percentiles(returns, ticker)
        st.dataframe(
            pd.DataFrame({"Daily Return": percentiles}).style.format("{:.4%}"), use_container_width=True
        )
    render_divider()

    # ---- Return Distribution (Histogram) ----
    render_section_header("Return Distribution", subtitle="Histogram with mean and median markers", icon="📉")
    st.plotly_chart(
        build_return_histogram(returns), use_container_width=True, config=CHART_CONFIG, key=f"desc_hist_{ticker}"
    )
    render_divider()

    # ---- Box Plot ----
    render_section_header("Box Plot", subtitle="Median, quartiles, and outliers", icon="📦")
    st.plotly_chart(
        build_return_box_plot(returns), use_container_width=True, config=CHART_CONFIG, key=f"desc_box_{ticker}"
    )
    render_divider()

    # ---- Outlier Analysis (IQR) ----
    render_section_header("Outlier Analysis (IQR Method)", subtitle="Analysis only -- no data is removed", icon="🔎")
    outliers = detect_return_outliers(returns, ticker)
    col_o1, col_o2, col_o3, col_o4 = st.columns(4)
    with col_o1:
        st.metric("Total Observations", outliers["total_observations"])
    with col_o2:
        st.metric("Normal Observations", outliers["normal_observations"])
    with col_o3:
        st.metric("Outliers", outliers["outlier_count"])
    with col_o4:
        st.metric("Lower / Upper Outliers", f"{outliers['lower_outlier_count']} / {outliers['upper_outlier_count']}")
    st.caption(
        f"Q1 = {outliers['q1']:.4%}, Q3 = {outliers['q3']:.4%}, IQR = {outliers['iqr']:.4%}  |  "
        f"Lower Bound = {outliers['lower_bound']:.4%}, Upper Bound = {outliers['upper_bound']:.4%}"
    )
    if outliers["outlier_count"] > 0:
        with st.expander(f"View {outliers['outlier_count']} outlier observation(s)"):
            display_table = outliers["outlier_table"].copy()
            display_table["Daily Return"] = display_table["Daily Return"].map(lambda v: f"{v:.4%}")
            st.dataframe(display_table, use_container_width=True, hide_index=True)
    else:
        st.info("No outliers detected in this period under the IQR rule.")
    render_divider()

    # ---- Distribution Shape ----
    render_section_header("Distribution Shape", subtitle="Skewness and kurtosis, plainly explained", icon="🔬")
    col_shape1, col_shape2 = st.columns(2)
    with col_shape1:
        st.metric("Skewness", f"{return_stats['skewness']:.4f}")
        st.caption(describe_skewness(return_stats["skewness"]))
    with col_shape2:
        st.metric("Kurtosis (excess)", f"{return_stats['kurtosis']:.4f}")
        st.caption(describe_kurtosis(return_stats["kurtosis"]))
    render_divider()

    # ---- Volatility ----
    render_section_header("Volatility", subtitle="Rolling and annualized volatility of daily returns", icon="⚡")
    volatility = calculate_volatility(returns, ticker)
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    with col_v1:
        value = volatility["volatility_5_day"]
        st.metric("5-Day Volatility", f"{value:.4%}" if value is not None else "N/A")
    with col_v2:
        value = volatility["volatility_10_day"]
        st.metric("10-Day Volatility", f"{value:.4%}" if value is not None else "N/A")
    with col_v3:
        value = volatility["volatility_20_day"]
        st.metric("20-Day Volatility", f"{value:.4%}" if value is not None else "N/A")
    with col_v4:
        st.metric("Annualized Volatility", f"{volatility['annualized_volatility_pct']:.2f}%")


def _render_descriptive_statistics_tab(user_id: int | None) -> None:
    st.caption(
        "Descriptive statistics and return-distribution analysis for a single stock -- price statistics, "
        "return statistics, quartiles/percentiles, histogram, box plot, IQR outlier detection, distribution "
        "shape, and volatility. This is analysis only and does not constitute a buy/sell recommendation."
    )

    col1, col2 = st.columns(2)
    with col1:
        query = st.text_input("Stock", placeholder="e.g. TCS, RELIANCE.NS, AAPL", key="descstats_ticker")
    with col2:
        period_label = st.select_slider(
            "Time Range", options=list(PERIOD_OPTIONS.keys()), value="1 Year", key="descstats_period"
        )
    period = PERIOD_OPTIONS[period_label]

    if st.button("Run Descriptive Statistics", type="primary", key="descstats_run"):
        if not query.strip():
            st.warning("Enter a stock to analyze.")
            return

        with st.spinner("Fetching price history and computing descriptive statistics..."):
            ticker = _resolve_and_validate(query)
            if ticker is None:
                return

            history = get_historical_data(ticker, period)
            if history is None or history.empty:
                st.info(f"Historical data is not available for {ticker} over the selected range.")
                return

            returns = get_daily_returns(ticker, period)

        _render_descriptive_statistics_result(ticker, history, returns)
        _safe_audit_log(
            action="STATISTICS_DESCRIPTIVE_RUN",
            user_id=user_id,
            entity_type="ticker",
            details=f"{ticker} descriptive statistics ({period_label})",
        )


def _render_t_test_tab(user_id: int | None) -> None:
    st.caption(
        "Compares the mean daily return of two independent groups using an independent-samples T-test "
        "(`scipy.stats.ttest_ind`). Variance equality is checked first with Levene's test, so Welch's "
        "correction is applied automatically when the two groups' variances differ."
    )

    comparison_mode = st.radio(
        "Comparison type",
        ["Two Stocks", "Bullish vs Bearish (single stock)"],
        horizontal=True,
        key="ttest_mode",
    )

    period_label = st.select_slider("Time Range", options=list(PERIOD_OPTIONS.keys()), value="1 Year", key="ttest_period")
    period = PERIOD_OPTIONS[period_label]

    if comparison_mode == "Two Stocks":
        col1, col2 = st.columns(2)
        with col1:
            query_a = st.text_input("Stock A", placeholder="e.g. TCS, RELIANCE.NS, AAPL", key="ttest_ticker_a")
        with col2:
            query_b = st.text_input("Stock B", placeholder="e.g. INFY, HDFCBANK.NS, MSFT", key="ttest_ticker_b")

        if st.button("Run T-Test", type="primary", key="ttest_run_two_stocks"):
            if not query_a.strip() or not query_b.strip():
                st.warning("Enter both stocks to compare.")
                return

            with st.spinner("Fetching price history and running the T-test..."):
                ticker_a = _resolve_and_validate(query_a)
                ticker_b = _resolve_and_validate(query_b)
                if ticker_a is None or ticker_b is None:
                    return

                returns_a = get_daily_returns(ticker_a, period)
                returns_b = get_daily_returns(ticker_b, period)
                result = perform_t_test(returns_a, returns_b, ticker_a, ticker_b, metric_name="daily return")

            _render_t_test_result(result)
            _safe_audit_log(
                action="STATISTICS_T_TEST_RUN",
                user_id=user_id,
                entity_type="ticker_pair",
                details=f"{ticker_a} vs {ticker_b} ({period_label}) -> {result['decision']}",
            )

    else:
        query = st.text_input("Stock", placeholder="e.g. TCS, RELIANCE.NS, AAPL", key="ttest_ticker_single")

        if st.button("Run T-Test", type="primary", key="ttest_run_bull_bear"):
            if not query.strip():
                st.warning("Enter a stock to analyze.")
                return

            with st.spinner("Fetching price history and running the T-test..."):
                ticker = _resolve_and_validate(query)
                if ticker is None:
                    return

                bullish, bearish = get_bullish_bearish_returns(ticker, period)
                result = perform_t_test(
                    bullish, bearish, "Bullish Days", "Bearish Days", metric_name="daily return"
                )

            st.caption(f"'Bullish' = days {ticker}'s close was above its 20-day SMA; 'Bearish' = at or below it.")
            _render_t_test_result(result)
            _safe_audit_log(
                action="STATISTICS_T_TEST_RUN",
                user_id=user_id,
                entity_type="ticker",
                details=f"{ticker} bullish vs bearish ({period_label}) -> {result['decision']}",
            )


def _render_chi_square_tab(user_id: int | None) -> None:
    st.caption(
        "Tests whether FinSight AI's existing RSI-based BUY/SELL/NEUTRAL signal is associated with the "
        "actual next-day price direction, using a Chi-square test of independence "
        "(`scipy.stats.chi2_contingency`) on a full history of daily signals."
    )

    col1, col2 = st.columns(2)
    with col1:
        query = st.text_input("Stock", placeholder="e.g. TCS, RELIANCE.NS, AAPL", key="chisq_ticker")
    with col2:
        period_label = st.select_slider(
            "Time Range", options=list(PERIOD_OPTIONS.keys()), value="1 Year", key="chisq_period"
        )
    period = PERIOD_OPTIONS[period_label]

    if st.button("Run Chi-Square Test", type="primary", key="chisq_run"):
        if not query.strip():
            st.warning("Enter a stock to analyze.")
            return

        with st.spinner("Fetching price history and running the Chi-square test..."):
            ticker = _resolve_and_validate(query)
            if ticker is None:
                return

            dataset = get_rsi_signal_vs_next_day_movement(ticker, period)
            result = perform_chi_square_test(
                dataset["RSI Signal"], dataset["Next-Day Movement"], "RSI Signal", "Next-Day Movement"
            )

        _render_chi_square_result(result)
        _safe_audit_log(
            action="STATISTICS_CHI_SQUARE_TEST_RUN",
            user_id=user_id,
            entity_type="ticker",
            details=f"{ticker} RSI signal vs next-day movement ({period_label}) -> {result['decision']}",
        )


@login_required
def render() -> None:
    """Render the full Statistical Analysis page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("📐 Statistical Analysis")
        st.caption("Hypothesis testing on real FinSight AI market data — T-Test and Chi-Square.")
        render_divider()

        descriptive_tab, t_test_tab, chi_square_tab = st.tabs(
            ["📐 Descriptive Statistics", "📊 T-Test", "🔬 Chi-Square Test"]
        )

        with descriptive_tab:
            render_section_header(
                "Descriptive Statistics", subtitle="Price/return statistics and distribution analysis", icon="📐"
            )
            _render_descriptive_statistics_tab(user_id)

        with t_test_tab:
            render_section_header("T-Test", subtitle="Compare mean returns between two independent groups", icon="📊")
            _render_t_test_tab(user_id)

        with chi_square_tab:
            render_section_header(
                "Chi-Square Test", subtitle="Test for association between two categorical variables", icon="🔬"
            )
            _render_chi_square_tab(user_id)

    except ValidationError as exc:
        st.warning(exc.message)
    except DataProcessingError as exc:
        st.error(exc.message)
    except FinSightBaseException as exc:
        logger.error(f"Handled error in statistical analysis: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in statistical analysis: {exc}")
        st.error("An unexpected error occurred while running the statistical analysis. Please try again.")