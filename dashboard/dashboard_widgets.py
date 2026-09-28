"""
dashboard/dashboard_widgets.py

Purpose: Reusable, data-driven UI components for the dashboard --
animated KPI cards (with optional Plotly sparkline), gainers/losers/
most-active data tables, and the market-status badge. Every dashboard
page (market_indices.py, top_gainers.py, ...) composes its layout out
of these instead of hand-writing HTML/Streamlit calls repeatedly.
"""

from typing import Any

import streamlit as st

from dashboard.chart_helpers import build_sparkline
from dashboard.market_data_service import NIFTY50_UNIVERSE
from helper import format_currency, format_percentage


def render_kpi_card(
    label: str,
    price: float,
    change: float,
    change_pct: float,
    currency_symbol: str = "",
    sparkline_prices: list[float] | None = None,
) -> None:
    """
    Render a single animated KPI card: label, formatted price, and a
    colored change/change% line, with an optional embedded sparkline.
    Used for indices, commodities, crypto, and forex on the Overview tab.
    """
    is_positive = change >= 0
    change_class = "kpi-change-positive" if is_positive else "kpi-change-negative"
    arrow = "▲" if is_positive else "▼"
    formatted_price = f"{currency_symbol}{price:,.2f}" if currency_symbol else f"{price:,.2f}"

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{formatted_price}</div>
            <div class="{change_class}">{arrow} {abs(change):,.2f} ({format_percentage(change_pct)})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if sparkline_prices and len(sparkline_prices) > 1:
        fig = build_sparkline(sparkline_prices, change_positive=is_positive)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"spark_{label}")


def render_kpi_card_placeholder(label: str) -> None:
    """Render a graceful "data unavailable" KPI card when a quote fetch fails."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="opacity:0.4;">--</div>
            <div style="opacity:0.4; font-size:0.85rem;">Data unavailable</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_market_status_badge(is_open: bool, label: str, as_of_str: str) -> None:
    """Render the green/red pill badge showing whether the market is currently open."""
    css_class = "status-badge-open" if is_open else "status-badge-closed"
    dot = "🟢" if is_open else "🔴"
    st.markdown(
        f"""
        <div class="status-badge {css_class}">{dot} {label} &nbsp;•&nbsp; as of {as_of_str} IST</div>
        """,
        unsafe_allow_html=True,
    )


def build_mover_rows(quotes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert raw quote dicts into the row shape expected by
    `render_movers_table`. Shared by top_gainers.py, top_losers.py, and
    most_active.py so this conversion logic exists in exactly one place
    instead of being copy-pasted across all three.
    """
    return [
        {
            "ticker": ticker,
            "company": NIFTY50_UNIVERSE.get(ticker, ticker),
            "price": quote["price"],
            "change": quote["change"],
            "change_pct": quote["change_pct"],
            "volume": quote["volume"],
        }
        for ticker, quote in quotes.items()
    ]


def select_stock_and_navigate(ticker: str) -> None:
    """
    Navigate to Stock Search with a specific ticker pre-loaded. Shared
    by every clickable-ticker surface in the app (Dashboard movers,
    Watchlist, Portfolio holdings/recommendations, Trending Stocks) so
    the click-to-navigate behavior lives in exactly one place.
    """
    st.session_state["selected_stock"] = ticker
    st.session_state["nav_target"] = "stock_search"
    st.rerun()


def render_clickable_ticker(ticker: str, label: str | None = None, key: str | None = None) -> None:
    """
    Render a single ticker as a clickable button that navigates to
    Stock Search with that ticker pre-loaded. `label` defaults to the
    ticker itself; pass a custom label (e.g. "TCS.NS — Reliance...")
    for richer display contexts.
    """
    display_label = label or ticker
    button_key = key or f"clickable_ticker_{ticker}_{hash(display_label) % 1_000_000}"
    if st.button(display_label, key=button_key, use_container_width=True):
        select_stock_and_navigate(ticker)


def render_movers_table(rows: list[dict[str, Any]], empty_message: str = "No data available.") -> None:
    """
    Render a Company / Current Price / Change / Change % / Volume table,
    used identically by top_gainers.py, top_losers.py, and most_active.py.
    Each row's company/ticker cell is clickable: clicking it sets
    `st.session_state["selected_stock"]` to that ticker, navigates to
    Stock Search, and reruns -- letting a user jump straight from a
    mover list into full company analysis.

    Args:
        rows: list of {"company": str, "ticker": str, "price": float,
                        "change": float, "change_pct": float, "volume": int}
    """
    if not rows:
        st.info(empty_message)
        return

    header_cols = st.columns([3, 2, 2, 2, 2])
    for col, title in zip(header_cols, ["Company", "Price", "Change", "Change %", "Volume"]):
        col.markdown(f"**{title}**")

    # id(rows) keeps widget keys unique across simultaneous calls on the
    # same page (e.g. Top Gainers and Top Losers rendered side by side)
    # without requiring a new parameter or any caller changes.
    table_id = id(rows)

    for index, row in enumerate(rows):
        is_positive = row["change"] >= 0
        change_color = "#22C55E" if is_positive else "#EF4444"
        arrow = "▲" if is_positive else "▼"

        cols = st.columns([3, 2, 2, 2, 2])
        with cols[0]:
            if st.button(
                f"{row['company']} ({row['ticker']})",
                key=f"mover_row_{table_id}_{index}_{row['ticker']}",
                use_container_width=True,
            ):
                select_stock_and_navigate(row["ticker"])
        cols[1].markdown(format_currency(row["price"], "₹"))
        cols[2].markdown(
            f"<span style='color:{change_color};'>{arrow} {format_currency(abs(row['change']), '₹')}</span>",
            unsafe_allow_html=True,
        )
        cols[3].markdown(
            f"<span style='color:{change_color};'>{format_percentage(row['change_pct'])}</span>",
            unsafe_allow_html=True,
        )
        cols[4].markdown(f"{row['volume']:,}")


def render_loading_placeholder(message: str = "Fetching live market data...") -> None:
    """Render a consistent loading placeholder while a data fetch is in progress."""
    st.markdown(
        f"""
        <div class="kpi-card" style="text-align:center; opacity:0.7;">
            ⏳ {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_snapshot_metric(label: str, value: str, delta: str | None = None) -> None:
    """Thin wrapper over st.metric for consistent labeling across portfolio/watchlist snapshots."""
    st.metric(label=label, value=value, delta=delta)