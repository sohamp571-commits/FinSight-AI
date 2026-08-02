"""
analytics/signal_generator.py

Purpose: Aggregates the individual BUY/SELL/NEUTRAL signals produced
by rsi.py, macd.py, bollinger_bands.py, stochastic.py, and
moving_average.py -- plus trend_analysis.py's strength read and
volume_chart.py's volume read -- into one consolidated recommendation
and an "Indicator Summary" table, exactly matching the Phase 6 Signals
requirement (Buy/Sell/Neutral Signal, Indicator Summary, Trend Strength).
"""

import pandas as pd
import streamlit as st

from analytics.bollinger_bands import calculate_bollinger_bands, get_bollinger_signal
from analytics.macd import calculate_macd, get_macd_signal
from analytics.moving_average import calculate_sma, get_ma_crossover_signal
from analytics.rsi import calculate_rsi, get_rsi_signal
from analytics.stochastic import calculate_stochastic, get_stochastic_signal
from analytics.trend_analysis import analyze_trend
from analytics.volume_chart import get_volume_signal

_SIGNAL_ICONS = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "NEUTRAL": "🟡 NEUTRAL"}


def generate_signals(df: pd.DataFrame) -> dict[str, str]:
    """
    Compute every indicator's individual signal for the given DataFrame.

    Returns:
        {"RSI": "BUY"/"SELL"/"NEUTRAL", "MACD": ..., "Bollinger Bands": ...,
         "Stochastic": ..., "Moving Average": ...}
    """
    close = df["Close"]
    latest_price = float(close.iloc[-1])

    rsi_series = calculate_rsi(close)
    macd_df = calculate_macd(close)
    bb_df = calculate_bollinger_bands(close)
    stoch_df = calculate_stochastic(df)
    sma_20 = calculate_sma(close, 20).iloc[-1]
    sma_50 = calculate_sma(close, 50).iloc[-1] if len(close) >= 50 else None

    return {
        "RSI": get_rsi_signal(float(rsi_series.iloc[-1]) if not rsi_series.empty else None),
        "MACD": get_macd_signal(macd_df),
        "Bollinger Bands": get_bollinger_signal(latest_price, bb_df.iloc[-1]),
        "Stochastic": get_stochastic_signal(stoch_df.iloc[-1]),
        "Moving Average": get_ma_crossover_signal(latest_price, sma_20, sma_50),
    }


def get_overall_recommendation(signals: dict[str, str]) -> tuple[str, int, int, int]:
    """
    Aggregate individual signals by simple majority vote.

    Returns:
        (overall_signal, buy_count, sell_count, neutral_count)
    """
    buy_count = sum(1 for s in signals.values() if s == "BUY")
    sell_count = sum(1 for s in signals.values() if s == "SELL")
    neutral_count = sum(1 for s in signals.values() if s == "NEUTRAL")

    if buy_count > sell_count and buy_count > neutral_count:
        overall = "BUY"
    elif sell_count > buy_count and sell_count > neutral_count:
        overall = "SELL"
    else:
        overall = "NEUTRAL"

    return overall, buy_count, sell_count, neutral_count


def render_signal_summary(df: pd.DataFrame) -> None:
    """Render the full Signals tab: overall recommendation, indicator table, and trend strength."""
    signals = generate_signals(df)
    overall, buy_count, sell_count, neutral_count = get_overall_recommendation(signals)
    trend = analyze_trend(df)
    volume_read = get_volume_signal(df)

    overall_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[overall]
    st.markdown(f"## {overall_color} Overall Signal: {overall}")
    st.caption(f"Based on {len(signals)} indicators — {buy_count} Buy, {sell_count} Sell, {neutral_count} Neutral")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Trend", trend["direction"])
    with col2:
        st.metric("Trend Strength", trend["strength"])
    with col3:
        st.metric("Volume", volume_read)

    st.markdown("### Indicator Summary")
    summary_rows = [{"Indicator": name, "Signal": _SIGNAL_ICONS[value]} for name, value in signals.items()]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.caption(
        "⚠️ These signals are generated from technical indicators only and are for educational purposes. "
        "They are not financial advice."
    )
