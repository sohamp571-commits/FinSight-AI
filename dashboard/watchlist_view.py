"""
dashboard/watchlist_view.py

Purpose: A dedicated "My Watchlist" page. No standalone watchlist page
existed anywhere in the project before Phase 12 -- favoriting a ticker
was only reachable from within Stock Search (Phase 5). This file adds
the missing view the Phase 12 sidebar links to, reusing
`database.watchlist_service` (Phase 3) and
`dashboard.market_data_service` (Phase 4) for every number shown.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_empty_state, render_section_header
from dashboard.market_data_service import fetch_quotes_bulk
from database.watchlist_service import watchlist_service
from helper import format_currency, format_percentage
from logging_config import logger


@login_required
def render() -> None:
    """Render the full Watchlist page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("⭐ My Watchlist")
        st.caption("Tickers you're tracking. Add more from the Stock Search page.")
        render_divider()

        entries = watchlist_service.list_watchlist(user_id, page_size=100)["items"]

        if not entries:
            clicked = render_empty_state(
                "Your watchlist is empty. Search for a company on the Stock Search page and tap ☆ to add it.",
                icon="⭐", action_label="🔍 Go to Stock Search",
            )
            if clicked:
                st.session_state["nav_target"] = "stock_search"
                st.rerun()
            return

        tickers = tuple(sorted({e.ticker_symbol for e in entries}))
        quotes = fetch_quotes_bulk(tickers)

        render_section_header("Tracked Tickers", subtitle=f"{len(entries)} ticker(s)", icon="⭐")

        header_cols = st.columns([2, 2, 2, 2, 1])
        for col, title in zip(header_cols, ["Ticker", "Price", "Change", "Change %", ""]):
            col.markdown(f"**{title}**")

        for entry in entries:
            quote = quotes.get(entry.ticker_symbol)
            cols = st.columns([2, 2, 2, 2, 1])
            cols[0].markdown(f"**{entry.ticker_symbol}**")

            if quote is None:
                cols[1].write("N/A")
                cols[2].write("N/A")
                cols[3].write("N/A")
            else:
                is_positive = quote["change_pct"] >= 0
                color = "#22C55E" if is_positive else "#EF4444"
                arrow = "▲" if is_positive else "▼"
                cols[1].write(format_currency(quote["price"], "₹"))
                cols[2].markdown(
                    f"<span style='color:{color};'>{arrow} {format_currency(abs(quote['change']), '₹')}</span>",
                    unsafe_allow_html=True,
                )
                cols[3].markdown(
                    f"<span style='color:{color};'>{format_percentage(quote['change_pct'])}</span>",
                    unsafe_allow_html=True,
                )

            if cols[4].button("🗑️", key=f"remove_watchlist_{entry.watchlist_id}"):
                try:
                    watchlist_service.remove_stock(user_id, entry.ticker_symbol)
                    st.rerun()
                except FinSightBaseException as exc:
                    logger.error(f"Failed to remove {entry.ticker_symbol} from watchlist: {exc}")
                    st.error("Could not remove this ticker right now.")

    except FinSightBaseException as exc:
        logger.error(f"Handled error in watchlist view: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in watchlist view: {exc}")
        st.error("An unexpected error occurred while loading your watchlist. Please try again.")
