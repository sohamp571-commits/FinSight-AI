"""
portfolio/performance_metrics.py

Purpose: Computes portfolio-level risk/return statistics -- Expected
Return, Volatility, Sharpe Ratio, Beta, and Max Drawdown. Reuses
`analytics.indicator_service.get_ohlcv()` (Phase 6's cached/retried
data layer) for every holding's price history and for the NIFTY 50
benchmark used in the Beta calculation, rather than issuing new
yfinance calls.

Methodology note: portfolio-level daily returns are approximated by
applying *today's* holding weights to each ticker's historical daily
returns (a standard, transparent simplification also used by most
retail portfolio trackers) rather than replaying the user's exact
historical transaction sequence, which would require a full
point-in-time position ledger the schema doesn't (and doesn't need to)
track.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from analytics.indicator_service import get_ohlcv
from dashboard.market_data_service import MARKET_INDICES
from portfolio.portfolio_calculator import compute_holding_weights
from portfolio.portfolio_service import get_portfolio_summary_live

TRADING_DAYS_PER_YEAR = 252
DEFAULT_RISK_FREE_RATE = 0.065  # ~ Indian 10-year G-Sec yield, used as the Sharpe Ratio benchmark
DEFAULT_TIMEFRAME = "1 Year"


@dataclass
class PerformanceMetrics:
    """Portfolio-level risk/return statistics."""

    expected_return_pct: float | None
    volatility_pct: float | None
    sharpe_ratio: float | None
    beta: float | None
    max_drawdown_pct: float | None


def _get_weighted_daily_returns(user_id: int, timeframe_label: str = DEFAULT_TIMEFRAME) -> pd.Series | None:
    """Build a weighted daily-returns series for the whole portfolio, using current holding weights."""
    summary = get_portfolio_summary_live(user_id)
    holdings = summary["holdings"]
    if not holdings:
        return None

    weights = compute_holding_weights(holdings)
    weighted_returns: pd.DataFrame | None = None

    for holding in holdings:
        ticker = holding["ticker_symbol"]
        weight = weights.get(ticker, 0.0) / 100
        if weight <= 0:
            continue

        history = get_ohlcv(ticker, timeframe_label)
        if history is None or len(history) < 20:
            continue

        daily_returns = history["Close"].pct_change().dropna() * weight
        if weighted_returns is None:
            weighted_returns = daily_returns.to_frame(name=ticker)
        else:
            weighted_returns = weighted_returns.join(daily_returns.to_frame(name=ticker), how="outer")

    if weighted_returns is None or weighted_returns.empty:
        return None

    return weighted_returns.fillna(0).sum(axis=1)


def compute_expected_return(returns_series: pd.Series) -> float:
    """Annualize the mean daily return into a percentage."""
    return round(float(returns_series.mean() * TRADING_DAYS_PER_YEAR) * 100, 2)


def compute_volatility(returns_series: pd.Series) -> float:
    """Annualize the standard deviation of daily returns into a percentage."""
    return round(float(returns_series.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) * 100, 2)


def compute_sharpe_ratio(returns_series: pd.Series, risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> float | None:
    """Compute the annualized Sharpe Ratio: (annualized return - risk-free rate) / annualized volatility."""
    annualized_return = returns_series.mean() * TRADING_DAYS_PER_YEAR
    annualized_volatility = returns_series.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    if annualized_volatility == 0 or pd.isna(annualized_volatility):
        return None
    return round(float((annualized_return - risk_free_rate) / annualized_volatility), 3)


def compute_beta(returns_series: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Compute Beta: covariance(portfolio, benchmark) / variance(benchmark), aligned by date."""
    aligned = pd.concat([returns_series, benchmark_returns], axis=1, join="inner").dropna()
    if len(aligned) < 20:
        return None

    covariance = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    benchmark_variance = aligned.iloc[:, 1].var()
    if benchmark_variance == 0:
        return None
    return round(float(covariance / benchmark_variance), 3)


def compute_max_drawdown(returns_series: pd.Series) -> float:
    """Compute maximum drawdown (%) from a cumulative-return curve built from daily returns."""
    cumulative = (1 + returns_series).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return round(float(drawdown.min()) * 100, 2)


def compute_performance_metrics(user_id: int, timeframe_label: str = DEFAULT_TIMEFRAME) -> PerformanceMetrics:
    """Compute the full performance metrics suite for a user's portfolio."""
    portfolio_returns = _get_weighted_daily_returns(user_id, timeframe_label)
    if portfolio_returns is None or len(portfolio_returns) < 20:
        return PerformanceMetrics(None, None, None, None, None)

    benchmark_history = get_ohlcv(MARKET_INDICES["NIFTY 50"], timeframe_label)
    benchmark_returns = benchmark_history["Close"].pct_change().dropna() if benchmark_history is not None else None

    return PerformanceMetrics(
        expected_return_pct=compute_expected_return(portfolio_returns),
        volatility_pct=compute_volatility(portfolio_returns),
        sharpe_ratio=compute_sharpe_ratio(portfolio_returns),
        beta=compute_beta(portfolio_returns, benchmark_returns) if benchmark_returns is not None else None,
        max_drawdown_pct=compute_max_drawdown(portfolio_returns),
    )
