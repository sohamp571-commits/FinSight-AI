"""
statistics/hypothesis_tests.py

Purpose: The business-logic layer for the Statistical Analysis module --
Streamlit-free, mirroring `stock_search/search_service.py`'s role in
that package (pure functions in, structured results out). Implements
two classical hypothesis tests on real FinSight AI market data:

    - perform_t_test(): an independent two-sample T-test (Welch's or
      Student's, chosen automatically) comparing the mean daily
      returns of two groups (e.g. two stocks, or two periods for the
      same stock).
    - perform_chi_square_test(): a Chi-square test of independence
      between two categorical variables (e.g. a technical signal and
      the next-day price direction it "predicted").

Both functions are pure: they take already-prepared numeric/categorical
data (see `statistics/data_preparation.py` for how FinSight AI's
existing price data is turned into that data) and return a plain,
JSON-serializable dict describing every step of the test -- hypotheses,
statistic, p-value, decision, and a human-readable interpretation --
so `statistics/statistical_dashboard.py` has nothing statistical left
to compute; it only renders.
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, levene, ttest_ind

from custom_exceptions import DataProcessingError, ValidationError
from logging_config import logger

# ==========================================================
# Shared configuration
# ==========================================================
SIGNIFICANCE_LEVEL: float = 0.05

# Below this many observations per group, a T-test's result is too
# unstable to present as meaningful for a viva/demo -- fail loudly
# and clearly instead of showing a misleading p-value.
MIN_SAMPLE_SIZE: int = 8

# Below this many total observations, a Chi-square contingency table
# is too sparse to trust.
MIN_CHI_SQUARE_OBSERVATIONS: int = 20


# ==========================================================
# T-Test
# ==========================================================
def perform_t_test(
    sample_a: pd.Series | np.ndarray,
    sample_b: pd.Series | np.ndarray,
    label_a: str,
    label_b: str,
    metric_name: str = "daily return",
) -> dict[str, Any]:
    """
    Run an independent two-sample T-test comparing the mean of
    `sample_a` against the mean of `sample_b`.

    Statistical correctness (Part 9 of the brief):
        - Both samples are treated as *independent* observations (two
          different stocks' daily returns, or the same stock's returns
          in two non-overlapping periods) -- never paired -- so
          `scipy.stats.ttest_ind` is the correct test family.
        - Sample sizes and variances are rarely identical for two real
          stocks/periods, so Levene's test first checks the equal-
          variance assumption. If variances are significantly
          different (Levene p < 0.05), Welch's T-test (`equal_var=False`)
          is used instead of the standard Student's T-test -- this is
          the textbook-correct adjustment rather than blindly assuming
          equal variance.
        - NaN values (e.g. the first row of a `pct_change()` series)
          are dropped before the test; the test is refused with a
          clear error if either group ends up too small to be
          statistically meaningful.

    Args:
        sample_a: Numeric observations for group A.
        sample_b: Numeric observations for group B.
        label_a: Human-readable name for group A (e.g. a ticker symbol).
        label_b: Human-readable name for group B.
        metric_name: What the numbers represent, used in the generated
            hypothesis wording (e.g. "daily return").

    Returns:
        A dict with every value the UI needs to display: hypotheses,
        sample sizes, means/std-devs, the Levene pre-check, the T-test
        itself, and a plain-English interpretation.

    Raises:
        ValidationError: if either sample is empty or too small after
            cleaning.
    """
    series_a = pd.Series(sample_a).dropna().astype(float)
    series_b = pd.Series(sample_b).dropna().astype(float)

    if len(series_a) < MIN_SAMPLE_SIZE or len(series_b) < MIN_SAMPLE_SIZE:
        raise ValidationError(
            f"Not enough data to run a T-test: '{label_a}' has {len(series_a)} usable observation(s) and "
            f"'{label_b}' has {len(series_b)}, but at least {MIN_SAMPLE_SIZE} are required per group. "
            "Try a longer time period."
        )

    # --- Assumption check: equal variance (Levene's test) ---
    levene_stat, levene_p = levene(series_a, series_b)
    equal_var = bool(levene_p >= SIGNIFICANCE_LEVEL)

    # --- The T-test itself ---
    try:
        t_stat, p_value = ttest_ind(series_a, series_b, equal_var=equal_var)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"T-test computation failed for '{label_a}' vs '{label_b}': {exc}")
        raise DataProcessingError("Failed to compute the T-test for the selected data.") from exc

    reject_null = bool(p_value < SIGNIFICANCE_LEVEL)
    mean_a, mean_b = float(series_a.mean()), float(series_b.mean())

    h0 = f"There is no significant difference between the mean {metric_name} of {label_a} and {label_b}."
    h1 = f"There is a significant difference between the mean {metric_name} of {label_a} and {label_b}."

    if reject_null:
        decision = "Reject H0"
        interpretation = (
            f"Since the p-value ({p_value:.4f}) is less than α ({SIGNIFICANCE_LEVEL}), we reject the null "
            f"hypothesis. There is statistically significant evidence that the mean {metric_name} of "
            f"{label_a} ({mean_a:.4%}) differs from that of {label_b} ({mean_b:.4%})."
        )
    else:
        decision = "Fail to reject H0"
        interpretation = (
            f"Since the p-value ({p_value:.4f}) is greater than or equal to α ({SIGNIFICANCE_LEVEL}), we fail "
            f"to reject the null hypothesis. There is insufficient statistical evidence that the mean "
            f"{metric_name} of {label_a} ({mean_a:.4%}) differs from that of {label_b} ({mean_b:.4%})."
        )

    logger.info(
        f"T-test executed: {label_a} (n={len(series_a)}) vs {label_b} (n={len(series_b)}), "
        f"t={t_stat:.4f}, p={p_value:.4f}, equal_var={equal_var}, decision='{decision}'"
    )

    return {
        "test_name": "Independent Two-Sample T-Test" if equal_var else "Welch's T-Test (unequal variances)",
        "group_a_label": label_a,
        "group_b_label": label_b,
        "metric_name": metric_name,
        "n_a": int(len(series_a)),
        "n_b": int(len(series_b)),
        "mean_a": mean_a,
        "mean_b": mean_b,
        "std_a": float(series_a.std(ddof=1)),
        "std_b": float(series_b.std(ddof=1)),
        "levene_stat": float(levene_stat),
        "levene_p_value": float(levene_p),
        "equal_var_assumed": equal_var,
        "t_statistic": float(t_stat),
        "p_value": float(p_value),
        "alpha": SIGNIFICANCE_LEVEL,
        "null_hypothesis": h0,
        "alternative_hypothesis": h1,
        "reject_null": reject_null,
        "decision": decision,
        "interpretation": interpretation,
        "series_a": series_a,
        "series_b": series_b,
    }


# ==========================================================
# Chi-Square Test of Independence
# ==========================================================
def perform_chi_square_test(
    variable_a: pd.Series,
    variable_b: pd.Series,
    label_a: str,
    label_b: str,
) -> dict[str, Any]:
    """
    Run a Chi-square test of independence between two categorical
    variables of equal length (e.g. a per-day technical signal and
    the next day's actual price direction).

    Statistical correctness (Part 9 of the brief):
        - Both inputs must already be categorical (string) labels, not
          continuous numbers -- `statistics/data_preparation.py` is
          responsible for that conversion (e.g. RSI value -> "BUY"/
          "SELL"/"NEUTRAL"; price change -> "UP"/"DOWN").
        - A contingency (cross-tab) table is built with
          `pandas.crosstab`, then passed to `scipy.stats.chi2_contingency`.
        - Chi-square's standard assumption is that at least 80% of
          expected-frequency cells are >= 5. That's checked after the
          test runs (expected frequencies are a byproduct of the same
          call) and surfaced as `low_expected_frequency_warning` rather
          than silently hidden, so the result is presented honestly
          even when the data is a little sparse -- which is realistic
          for a college-scale demo dataset.

    Args:
        variable_a: Categorical labels for variable A (e.g. RSI signal).
        variable_b: Categorical labels for variable B (e.g. next-day
            movement), aligned index-for-index with `variable_a`.
        label_a: Human-readable name for variable A.
        label_b: Human-readable name for variable B.

    Returns:
        A dict with the contingency table (observed + expected),
        hypotheses, statistic, p-value, decision, and interpretation.

    Raises:
        ValidationError: if there isn't enough paired data, or either
            variable has fewer than 2 distinct categories (Chi-square
            is undefined for a 1-category variable).
    """
    paired = pd.DataFrame({label_a: variable_a, label_b: variable_b}).dropna()

    if len(paired) < MIN_CHI_SQUARE_OBSERVATIONS:
        raise ValidationError(
            f"Not enough paired observations to run a Chi-square test: {len(paired)} available, but at least "
            f"{MIN_CHI_SQUARE_OBSERVATIONS} are required. Try a longer time period."
        )

    if paired[label_a].nunique() < 2 or paired[label_b].nunique() < 2:
        raise ValidationError(
            "Chi-square requires each variable to have at least two distinct categories in the observed data."
        )

    contingency_table = pd.crosstab(paired[label_a], paired[label_b])

    try:
        chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Chi-square computation failed for '{label_a}' vs '{label_b}': {exc}")
        raise DataProcessingError("Failed to compute the Chi-square test for the selected data.") from exc

    expected_df = pd.DataFrame(expected, index=contingency_table.index, columns=contingency_table.columns)
    low_expected_freq_warning = bool((expected_df < 5).mean().mean() > 0.20)

    reject_null = bool(p_value < SIGNIFICANCE_LEVEL)

    h0 = f"There is no significant association between {label_a} and {label_b}."
    h1 = f"There is a significant association between {label_a} and {label_b}."

    if reject_null:
        decision = "Reject H0"
        interpretation = (
            f"Since the p-value ({p_value:.4f}) is less than α ({SIGNIFICANCE_LEVEL}), we reject the null "
            f"hypothesis. There is statistically significant evidence of an association between {label_a} "
            f"and {label_b}."
        )
    else:
        decision = "Fail to reject H0"
        interpretation = (
            f"Since the p-value ({p_value:.4f}) is greater than or equal to α ({SIGNIFICANCE_LEVEL}), we fail "
            f"to reject the null hypothesis. There is insufficient statistical evidence of an association "
            f"between {label_a} and {label_b}."
        )

    if low_expected_freq_warning:
        interpretation += (
            " Note: more than 20% of the contingency table's expected cell frequencies are below 5, so this "
            "result should be treated as indicative rather than definitive -- a larger date range would make "
            "it more reliable."
        )

    logger.info(
        f"Chi-square test executed: {label_a} vs {label_b} (n={len(paired)}), "
        f"chi2={chi2_stat:.4f}, dof={dof}, p={p_value:.4f}, decision='{decision}'"
    )

    return {
        "test_name": "Chi-Square Test of Independence",
        "variable_a_label": label_a,
        "variable_b_label": label_b,
        "n_observations": int(len(paired)),
        "observed": contingency_table,
        "expected": expected_df,
        "chi2_statistic": float(chi2_stat),
        "degrees_of_freedom": int(dof),
        "p_value": float(p_value),
        "alpha": SIGNIFICANCE_LEVEL,
        "null_hypothesis": h0,
        "alternative_hypothesis": h1,
        "reject_null": reject_null,
        "decision": decision,
        "low_expected_frequency_warning": low_expected_freq_warning,
        "interpretation": interpretation,
    }