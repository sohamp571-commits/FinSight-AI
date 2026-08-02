"""
analytics package

Phase 6 — Technical Analysis & Advanced Charts for FinSight AI.

Sub-modules:
    indicator_service.py     - multi-timeframe OHLCV data access (own cache/retry)
    moving_average.py         - SMA / EMA / WMA
    rsi.py                     - Relative Strength Index
    macd.py                     - MACD line / signal / histogram
    bollinger_bands.py          - Bollinger Bands
    stochastic.py                - Stochastic Oscillator (%K / %D)
    atr.py                        - Average True Range (volatility)
    adx.py                         - Average Directional Index (trend strength)
    support_resistance.py          - Fractal-based support/resistance levels
    trend_analysis.py               - Combined trend direction & strength
    technical_indicators.py          - Aggregates every indicator into one summary
    candlestick_chart.py              - Interactive candlestick chart with overlays
    line_chart.py                      - Interactive line chart
    area_chart.py                       - Interactive area chart
    volume_chart.py                      - Volume chart with volume moving average
    signal_generator.py                   - BUY/SELL/NEUTRAL signal aggregation
    technical_analysis.py                  - main controller (entry point: technical_analysis.render)
"""

from analytics.technical_analysis import render

__all__ = ["render"]
