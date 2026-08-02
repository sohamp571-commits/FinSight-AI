"""
machine_learning/feature_engineering.py

Purpose: Transforms raw OHLCV data into the feature matrix used for
training. Reuses every indicator calculation already implemented in
`analytics/` (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX,
Stochastic) instead of re-deriving them, per the Phase 7 instruction
to reuse existing logic -- then adds the ML-specific features that
have no charting equivalent: returns, log returns, lag features,
rolling statistics, volatility, and momentum.
"""

import numpy as np
import pandas as pd

from analytics.adx import calculate_adx
from analytics.atr import calculate_atr
from analytics.bollinger_bands import calculate_bollinger_bands
from analytics.macd import calculate_macd
from analytics.moving_average import calculate_ema, calculate_sma
from analytics.rsi import calculate_rsi
from analytics.stochastic import calculate_stochastic

DEFAULT_LAG_PERIODS = (1, 2, 3, 5, 10)
DEFAULT_ROLLING_WINDOWS = (5, 10, 20)


def add_return_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add simple daily returns and log returns."""
    df = df.copy()
    df["returns"] = df["Close"].pct_change()
    df["log_returns"] = np.log(df["Close"] / df["Close"].shift(1))
    return df


def add_indicator_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add every technical indicator from analytics/ as a model feature column."""
    df = df.copy()
    close = df["Close"]

    df["sma_10"] = calculate_sma(close, 10)
    df["sma_20"] = calculate_sma(close, 20)
    df["sma_50"] = calculate_sma(close, 50)
    df["ema_12"] = calculate_ema(close, 12)
    df["ema_26"] = calculate_ema(close, 26)
    df["rsi_14"] = calculate_rsi(close)

    macd_df = calculate_macd(close)
    df["macd"] = macd_df["macd"]
    df["macd_signal"] = macd_df["signal"]
    df["macd_histogram"] = macd_df["histogram"]

    bb_df = calculate_bollinger_bands(close)
    df["bb_upper"] = bb_df["upper"]
    df["bb_middle"] = bb_df["middle"]
    df["bb_lower"] = bb_df["lower"]
    df["bb_width"] = (bb_df["upper"] - bb_df["lower"]) / bb_df["middle"]

    df["atr_14"] = calculate_atr(df[["High", "Low", "Close"]])

    adx_df = calculate_adx(df[["High", "Low", "Close"]])
    df["adx"] = adx_df["adx"]
    df["plus_di"] = adx_df["plus_di"]
    df["minus_di"] = adx_df["minus_di"]

    stoch_df = calculate_stochastic(df[["High", "Low", "Close"]])
    df["stoch_k"] = stoch_df["%K"]
    df["stoch_d"] = stoch_df["%D"]

    return df


def add_lag_features(df: pd.DataFrame, periods: tuple[int, ...] = DEFAULT_LAG_PERIODS) -> pd.DataFrame:
    """Add lagged closing prices and lagged returns -- the model's memory of recent history."""
    df = df.copy()
    for lag in periods:
        df[f"close_lag_{lag}"] = df["Close"].shift(lag)
        df[f"returns_lag_{lag}"] = df["returns"].shift(lag) if "returns" in df.columns else df["Close"].pct_change().shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, windows: tuple[int, ...] = DEFAULT_ROLLING_WINDOWS) -> pd.DataFrame:
    """Add rolling mean, rolling standard deviation (volatility), and momentum features."""
    df = df.copy()
    for window in windows:
        df[f"rolling_mean_{window}"] = df["Close"].rolling(window=window, min_periods=window).mean()
        df[f"rolling_std_{window}"] = df["Close"].rolling(window=window, min_periods=window).std()

    # Volatility: rolling std of returns, annualization not applied (kept as a raw model feature).
    df["volatility_10"] = df["Close"].pct_change().rolling(window=10, min_periods=10).std()
    df["volatility_20"] = df["Close"].pct_change().rolling(window=20, min_periods=20).std()

    # Momentum: price change over a fixed window.
    df["momentum_5"] = df["Close"] - df["Close"].shift(5)
    df["momentum_10"] = df["Close"] - df["Close"].shift(10)

    return df


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full feature engineering pipeline: returns -> indicators ->
    lag features -> rolling/volatility/momentum features, in that order
    (later steps depend on columns created by earlier ones).
    """
    df = add_return_features(df)
    df = add_indicator_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return every engineered feature column name (everything except the raw OHLCV columns)."""
    raw_columns = {"Open", "High", "Low", "Close", "Volume"}
    return [col for col in df.columns if col not in raw_columns]


def add_target_column(df: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    """Add the prediction target: the closing price `horizon_days` trading days into the future."""
    df = df.copy()
    df["target"] = df["Close"].shift(-horizon_days)
    return df
