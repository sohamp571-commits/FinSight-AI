"""
statistics/descriptive_statistics.py

Purpose: The business-logic layer for the Descriptive Statistics &
Return Distribution Analysis feature -- Streamlit-free, mirroring
`statistics/hypothesis_tests.py`'s role in this package (pure
functions in, structured results out).

This module contains no Streamlit calls, no chart building, and no
data fetching of its own. It operates on the OHLCV `DataFrame` already
returned by `stock_search.historical_data.get_historical_data()` and
the return `Series` already returned by
`statistics.data_preparation.get_daily_returns()`, so it never issues
a second yfinance call for data the project already has.

Functions:
    calculate_price_statistics()   -- Open/High/Low/Close/Volume descriptive stats table
    calculate_return_statistics()  -- Mean/median/min/max/range/variance/std/skew/kurtosis of daily returns
    calculate_quartiles()          -- Q1/Q2/Q3 of daily returns
    calculate_percentiles()        -- P10/P25/P50/P75/P90 of daily returns
    calculate_skewness()           -- Skewness of daily returns
    calculate_kurtosis()           -- Excess kurtosis of daily returns
    detect_return_outliers()       -- IQR-based outlier detection on daily returns
    calculate_volatility()         -- 5/10/20-day rolling volatility + annualized volatility
    describe_skewness()            -- Plain-language description of a skewness value
    describe_kurtosis()            -- Plain-language description of a kurtosis value

GTU syllabus mapping is documented at the bottom of this file.
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from custom_exceptions import DataProcessingError, ValidationError
from logging_config import logger
from portfolio.performance_metrics import TRADING_DAYS_PER_YEAR, compute_volatility

# Minimum number of usable observations before a distribution-shape
# statistic (skewness/kurtosis) or a quartile/percentile breakdown is
# considered meaningful enough to display.
MIN_OBSERVATIONS: int = 5

_OHLCV_COLUMNS: tuple[str, ...] = ("Open", "High", "Low", "Close", "Volume")

# Variance/standard-deviation convention: this module uses SAMPLE statistics
# (ddof=1, Bessel's correction) everywhere -- in `_describe_column()` (price
# and return variance/std. dev.) and in the 5/10/20-day rolling volatility
# windows in `calculate_volatility()`. This matches pandas' own default
# (`Series.var()`/`Series.std()` default to ddof=1) and matches the existing
# `portfolio.performance_metrics.compute_volatility()`, which this module
# reuses for annualized volatility, so all reported dispersion figures use
# the same convention throughout the app.


# ==========================================================
# Internal helpers
# ==========================================================
def _clean_numeric_series(series: pd.Series) -> pd.Series:
    """Drop NaN/inf values from a numeric series so downstream stats never choke on them."""
    cleaned = pd.to_numeric(series, errors="coerce")
    cleaned = cleaned.replace([np.inf, -np.inf], np.nan).dropna()
    return cleaned


def _describe_column(series: pd.Series) -> dict[str, float]:
    """Compute the standard descriptive-statistics set for one numeric column."""
    cleaned = _clean_numeric_series(series)
    if cleaned.empty:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "range": float("nan"),
            "variance": float("nan"),
            "std_dev": float("nan"),
        }

    minimum = float(cleaned.min())
    maximum = float(cleaned.max())
    return {
        "mean": float(cleaned.mean()),
        "median": float(cleaned.median()),
        "min": minimum,
        "max": maximum,
        "range": maximum - minimum,
        "variance": float(cleaned.var(ddof=1)) if len(cleaned) > 1 else 0.0,
        "std_dev": float(cleaned.std(ddof=1)) if len(cleaned) > 1 else 0.0,
    }


def _validate_history(history: pd.DataFrame | None, ticker: str) -> pd.DataFrame:
    """Validate an OHLCV DataFrame before any descriptive-statistics computation runs on it."""
    if history is None or history.empty:
        raise DataProcessingError(f"No historical price data is available for {ticker} over the selected period.")

    missing = [col for col in _OHLCV_COLUMNS if col not in history.columns]
    if missing:
        raise DataProcessingError(
            f"Historical data for {ticker} is missing required column(s): {', '.join(missing)}."
        )
    return history


def _validate_returns(returns: pd.Series, ticker: str, min_observations: int = MIN_OBSERVATIONS) -> pd.Series:
    """Validate/clean a daily-return series before any statistic is computed on it."""
    cleaned = _clean_numeric_series(returns)
    if len(cleaned) < min_observations:
        raise ValidationError(
            f"Not enough daily-return observations for {ticker} to compute descriptive statistics: "
            f"found {len(cleaned)}, need at least {min_observations}. Try a longer time period."
        )
    return cleaned


# ==========================================================
# 1. Price Statistics
# ==========================================================
def calculate_price_statistics(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Compute Mean / Median / Min / Max / Range / Variance / Std. Dev.
    for each of Open, High, Low, Close, and Volume.

    Args:
        history: OHLCV DataFrame as returned by
            `stock_search.historical_data.get_historical_data()`.
        ticker: Ticker symbol, used only for error messages.

    Returns:
        A DataFrame indexed by statistic name, with one column per
        OHLCV field, ready for `st.dataframe()`.

    Raises:
        DataProcessingError: if `history` is empty or missing an
            expected OHLCV column.
    """
    history = _validate_history(history, ticker)

    stats_by_column: dict[str, dict[str, float]] = {
        column: _describe_column(history[column]) for column in _OHLCV_COLUMNS
    }
    table = pd.DataFrame(stats_by_column)
    table.index = ["Mean", "Median", "Minimum", "Maximum", "Range", "Variance", "Standard Deviation"]
    return table


# ==========================================================
# 2. Daily Return Statistics
# ==========================================================
def calculate_return_statistics(returns: pd.Series, ticker: str) -> dict[str, Any]:
    """
    Compute Mean / Median / Min / Max / Range / Variance / Std. Dev. /
    Skewness / Kurtosis for a daily-return series.

    Args:
        returns: Daily-return series, e.g. from
            `statistics.data_preparation.get_daily_returns()`.
        ticker: Ticker symbol, used only for error messages.

    Returns:
        A flat dict of float values keyed by statistic name (all
        return-based fields are plain decimals, e.g. 0.0123 = 1.23%,
        so the UI can apply its own percentage formatting).

    Raises:
        ValidationError: if there are too few usable observations.
    """
    cleaned = _validate_returns(returns, ticker)
    base = _describe_column(cleaned)

    return {
        "n_observations": int(len(cleaned)),
        "mean": base["mean"],
        "median": base["median"],
        "min": base["min"],
        "max": base["max"],
        "range": base["range"],
        "variance": base["variance"],
        "std_dev": base["std_dev"],
        "skewness": calculate_skewness(cleaned),
        "kurtosis": calculate_kurtosis(cleaned),
    }


def calculate_skewness(returns: pd.Series) -> float:
    """Sample skewness (Fisher-Pearson, bias-corrected) of a daily-return series."""
    cleaned = _clean_numeric_series(returns)
    if len(cleaned) < 3:
        return float("nan")
    return float(scipy_stats.skew(cleaned, bias=False))


def calculate_kurtosis(returns: pd.Series) -> float:
    """Sample excess kurtosis (Fisher's definition: normal distribution = 0) of a daily-return series."""
    cleaned = _clean_numeric_series(returns)
    if len(cleaned) < 4:
        return float("nan")
    return float(scipy_stats.kurtosis(cleaned, fisher=True, bias=False))


# ==========================================================
# 3. Quartiles and Percentiles
# ==========================================================
def calculate_quartiles(returns: pd.Series, ticker: str) -> dict[str, float]:
    """Compute Q1 (25th percentile), Q2 (50th percentile/median), and Q3 (75th percentile)."""
    cleaned = _validate_returns(returns, ticker)
    return {
        "Q1 (25th percentile)": float(cleaned.quantile(0.25)),
        "Q2 (50th percentile / Median)": float(cleaned.quantile(0.50)),
        "Q3 (75th percentile)": float(cleaned.quantile(0.75)),
    }


def calculate_percentiles(returns: pd.Series, ticker: str) -> dict[str, float]:
    """Compute P10, P25, P50, P75, and P90 of a daily-return series."""
    cleaned = _validate_returns(returns, ticker)
    return {
        "P10": float(cleaned.quantile(0.10)),
        "P25": float(cleaned.quantile(0.25)),
        "P50": float(cleaned.quantile(0.50)),
        "P75": float(cleaned.quantile(0.75)),
        "P90": float(cleaned.quantile(0.90)),
    }


# ==========================================================
# 6. IQR Outlier Detection
# ==========================================================
def detect_return_outliers(returns: pd.Series, ticker: str) -> dict[str, Any]:
    """
    Detect outliers in a daily-return series using the standard IQR
    rule (analysis only -- nothing is removed from the underlying data).

        IQR = Q3 - Q1
        Lower Bound = Q1 - 1.5 * IQR
        Upper Bound = Q3 + 1.5 * IQR

    Args:
        returns: Daily-return series, indexed by date.
        ticker: Ticker symbol, used only for error messages.

    Returns:
        A dict with the bounds, counts, and a DataFrame of the
        individual outlier rows (date + return value) for an
        expandable table.

    Raises:
        ValidationError: if there are too few usable observations.
    """
    cleaned = _validate_returns(returns, ticker)

    q1 = float(cleaned.quantile(0.25))
    q3 = float(cleaned.quantile(0.75))
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    lower_outliers = cleaned[cleaned < lower_bound]
    upper_outliers = cleaned[cleaned > upper_bound]
    outliers = pd.concat([lower_outliers, upper_outliers]).sort_index()

    outlier_table = outliers.rename("Daily Return").reset_index()
    outlier_table.columns = ["Date", "Daily Return"]

    total = int(len(cleaned))
    outlier_count = int(len(outliers))

    logger.info(
        f"IQR outlier detection for {ticker}: {outlier_count} outlier(s) out of {total} observation(s) "
        f"(bounds: [{lower_bound:.4f}, {upper_bound:.4f}])."
    )

    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "total_observations": total,
        "normal_observations": total - outlier_count,
        "outlier_count": outlier_count,
        "lower_outlier_count": int(len(lower_outliers)),
        "upper_outlier_count": int(len(upper_outliers)),
        "outlier_table": outlier_table,
    }


# ==========================================================
# 7. Volatility
# ==========================================================
def calculate_volatility(returns: pd.Series, ticker: str) -> dict[str, float | None]:
    """
    Compute short-window rolling volatility (5/10/20-day, std. dev. of
    daily returns over the trailing window) plus annualized volatility
    for the full period, reusing
    `portfolio.performance_metrics.compute_volatility()` for the
    annualization step rather than re-deriving it.

    A window's rolling figure is omitted (`None`) if the series has
    fewer observations than that window requires.

    Args:
        returns: Daily-return series, indexed by date (most recent last).
        ticker: Ticker symbol, used only for error messages.

    Raises:
        ValidationError: if there are too few usable observations for
            even the shortest (5-day) window.
    """
    cleaned = _validate_returns(returns, ticker, min_observations=5)

    windows = (5, 10, 20)
    rolling_volatility: dict[str, float | None] = {}
    for window in windows:
        if len(cleaned) >= window:
            rolling_volatility[f"{window}_day"] = float(cleaned.tail(window).std(ddof=1))
        else:
            rolling_volatility[f"{window}_day"] = None

    annualized_pct = compute_volatility(cleaned)  # already annualized + expressed as a percentage

    return {
        "volatility_5_day": rolling_volatility["5_day"],
        "volatility_10_day": rolling_volatility["10_day"],
        "volatility_20_day": rolling_volatility["20_day"],
        "annualized_volatility_pct": annualized_pct,
        "trading_days_per_year": TRADING_DAYS_PER_YEAR,
    }


# ==========================================================
# 8. Distribution Shape -- plain-language interpretation
# ==========================================================
def describe_skewness(skewness: float) -> str:
    """
    Plain-English description of a skewness value's direction/strength.
    Purely descriptive -- no investment recommendation.
    """
    if skewness is None or (isinstance(skewness, float) and np.isnan(skewness)):
        return "Skewness could not be computed for this sample."

    magnitude = abs(skewness)
    if magnitude < 0.5:
        strength = "approximately symmetric"
    elif magnitude < 1.0:
        strength = "moderately skewed"
    else:
        strength = "highly skewed"

    if skewness > 0.05:
        direction = "positively skewed (a longer tail toward larger positive returns)"
    elif skewness < -0.05:
        direction = "negatively skewed (a longer tail toward larger negative returns)"
    else:
        return f"The return distribution is approximately symmetric (skewness = {skewness:.4f})."

    return f"The return distribution is {strength} and {direction} (skewness = {skewness:.4f})."


def describe_kurtosis(kurtosis: float) -> str:
    """
    Plain-English description of an excess-kurtosis value's statistical
    meaning (tail thickness / peakedness relative to a normal
    distribution) -- not a judgment of whether that is "good" or "bad".
    """
    if kurtosis is None or (isinstance(kurtosis, float) and np.isnan(kurtosis)):
        return "Kurtosis could not be computed for this sample."

    if kurtosis > 1.0:
        return (
            f"Excess kurtosis of {kurtosis:.4f} indicates a leptokurtic distribution -- fatter tails and a "
            "sharper peak than a normal distribution, meaning extreme daily returns (in either direction) "
            "have occurred more often than a normal distribution would predict."
        )
    if kurtosis < -1.0:
        return (
            f"Excess kurtosis of {kurtosis:.4f} indicates a platykurtic distribution -- thinner tails and a "
            "flatter peak than a normal distribution, meaning extreme daily returns have been rarer than a "
            "normal distribution would predict."
        )
    return (
        f"Excess kurtosis of {kurtosis:.4f} is close to 0, indicating tail thickness roughly similar to a "
        "normal (mesokurtic) distribution."
    )


# ==========================================================
# GTU "Python for Data Science" syllabus mapping
# --------------------------------------------------------
# Feature (this module)                  -> GTU syllabus concept
# --------------------------------------------------------
# calculate_price_statistics()           -> Descriptive statistics; Pandas (data manipulation)
# calculate_return_statistics()          -> Measures of central tendency (mean, median);
#                                            Measures of dispersion/variation (variance, std. dev., range)
# calculate_quartiles() / calculate_percentiles()
#                                         -> Measures of location (quartiles, percentiles)
# calculate_skewness() / describe_skewness()
#                                         -> Shape and symmetry of a distribution
# calculate_kurtosis() / describe_kurtosis()
#                                         -> Shape and symmetry of a distribution
# detect_return_outliers()               -> Outlier handling/detection; Data preparation
# calculate_volatility()                 -> Measures of dispersion/variation; NumPy (numerical computation)
# Histogram / Box plot (rendered in statistical_dashboard.py)
#                                         -> Data visualization (Matplotlib/Seaborn-equivalent concepts,
#                                            implemented here with the project's existing Plotly charts)
# NumPy / Pandas / SciPy throughout      -> Pandas, NumPy; Data analysis
# ==========================================================
