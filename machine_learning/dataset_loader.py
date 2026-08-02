"""
machine_learning/dataset_loader.py

Purpose: The data-loading entry point for the ML pipeline. Reuses
`analytics.indicator_service.get_ohlcv()` (Phase 6's own cache/retry
layer over yfinance) rather than issuing a new type of API call --
per the Phase 7 instruction to reuse the existing yfinance service,
caching, and retry logic. Adds ML-specific concerns on top: a longer
default lookback window and a minimum-rows sufficiency check tuned
for model training (higher bar than charting needs).
"""

import pandas as pd

from analytics.indicator_service import TIMEFRAME_OPTIONS, get_ohlcv
from custom_exceptions import DataProcessingError
from logging_config import logger

# ML models need substantially more history than a chart does to learn
# meaningful patterns -- default to the longest practical daily-interval
# window available in TIMEFRAME_OPTIONS.
DEFAULT_TRAINING_TIMEFRAME = "5 Year"
MINIMUM_TRAINING_ROWS = 250  # roughly one trading year of daily bars


def load_training_dataset(ticker: str, timeframe_label: str = DEFAULT_TRAINING_TIMEFRAME) -> pd.DataFrame:
    """
    Load OHLCV data suitable for model training.

    Args:
        ticker: The resolved ticker symbol (see stock_search.search_service.resolve_ticker).
        timeframe_label: A key of analytics.indicator_service.TIMEFRAME_OPTIONS.

    Returns:
        A DataFrame with Open/High/Low/Close/Volume columns, sorted ascending by date.

    Raises:
        DataProcessingError: if data can't be fetched or there isn't enough
            history to train a reliable model.
    """
    if timeframe_label not in TIMEFRAME_OPTIONS:
        raise DataProcessingError(f"Unknown timeframe '{timeframe_label}' for model training.")

    df = get_ohlcv(ticker, timeframe_label)
    if df is None:
        raise DataProcessingError(f"Could not fetch historical data for {ticker}.")

    df = df.sort_index()
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])

    if len(df) < MINIMUM_TRAINING_ROWS:
        raise DataProcessingError(
            f"Only {len(df)} trading days of data are available for {ticker}; "
            f"at least {MINIMUM_TRAINING_ROWS} are required to train a reliable model. "
            f"Try a longer timeframe or a more established ticker."
        )

    logger.info(f"Loaded {len(df)} training rows for {ticker} ({timeframe_label}).")
    return df
