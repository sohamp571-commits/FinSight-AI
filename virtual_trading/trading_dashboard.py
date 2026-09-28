"""
virtual_trading/trading_dashboard.py

Purpose: The main entry point for Virtual Trading / Paper Trading,
following the exact same page structure as `portfolio/portfolio_dashboard.py`
(title + caption, injected dashboard CSS, KPI row, tabs) so it reads as
one integrated application rather than a bolted-on feature. Ties
together every virtual-trading backend piece -- `trading_service` for
account/holdings/transactions/BUY/SELL, `portfolio_calculator` for the
overview, `realized_pnl` for the sale-by-sale detail, `trading_stats`
for win/loss statistics -- plus `order_panel` (this package) for the
Trade tab. No calculation logic lives in this file; it only renders
what the backend already computed.

Isolation: every function in this file reads/writes exclusively
through `virtual_trading.trading_service`, which itself only calls
`database.virtual_account_service` / `virtual_holding_service` /
`virtual_transaction_service`. Nothing here ever touches
`portfolio.*`, `database.transaction_service`, or
`database.portfolio_service` (the real-money system) -- the two
systems are fully separate, matching the project's own Phase 13
migration design.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_empty_state, render_section_header
from database.audit_service import audit_service
from helper import format_currency, format_datetime, format_percentage
from logging_config import logger

from virtual_trading import order_panel, trading_service
from virtual_trading.portfolio_calculator import VirtualPortfolioOverview


# ==========================================================
# KPI row
# ==========================================================
def _render_kpi_row(overview: VirtualPortfolioOverview) -> None:
    row1 = st.columns(4)
    row1[0].metric("Cash Balance", format_currency(overview.cash_balance, "₹"))
    row1[1].metric("Invested Value", format_currency(overview.total_invested, "₹"))
    row1[2].metric("Current Holdings Value", format_currency(overview.current_holdings_value, "₹"))
    row1[3].metric(
        "Total Portfolio Value",
        format_currency(overview.total_portfolio_value, "₹"),
        help="Cash balance + current market value of your holdings.",
    )

    row2 = st.columns(4)
    row2[0].metric(
        "Unrealized P&L",
        format_currency(overview.unrealized_pnl, "₹"),
        delta=format_percentage(float(overview.unrealized_pnl_pct)),
        help="Profit/loss on positions you currently hold, marked to live market price.",
    )
    row2[1].metric(
        "Realized P&L",
        format_currency(overview.realized_pnl, "₹"),
        help="Profit/loss actually locked in by past virtual sales.",
    )
    row2[2].metric(
        "Today's P&L",
        format_currency(overview.todays_pnl, "₹"),
        delta=format_percentage(float(overview.todays_pnl_pct)),
    )
    row2[3].metric(
        "Total P&L",
        format_currency(overview.total_pnl, "₹"),
        delta=format_percentage(float(overview.return_pct)) + " return",
        help="Realized + Unrealized P&L, relative to your starting virtual capital.",
    )


# ==========================================================
# Trade tab
# ==========================================================
def _render_trade_tab(user_id: int) -> None:
    order_panel.render_order_panel(user_id)


# ==========================================================
# Portfolio / Holdings tab
# ==========================================================
def _render_portfolio_tab(overview: VirtualPortfolioOverview) -> None:
    render_section_header("Holdings", icon="📦")

    if not overview.holdings:
        render_empty_state(
            "You have no virtual holdings yet. Head to the Trade tab to make your first paper trade.",
            icon="💼",
        )
        return

    if any(not h.price_is_live for h in overview.holdings):
        st.caption("⚠️ Live prices were unavailable for one or more holdings below — shown at cost basis instead.")

    rows = [
        {
            "Ticker": h.ticker_symbol,
            "Quantity": f"{float(h.quantity):g}",
            "Avg. Buy Price": format_currency(h.average_buy_price, "₹"),
            "Current Price": format_currency(h.current_price, "₹") + ("" if h.price_is_live else " *"),
            "Invested Value": format_currency(h.invested_value, "₹"),
            "Current Value": format_currency(h.current_value, "₹"),
            "Unrealized P&L": format_currency(h.unrealized_pnl, "₹"),
            "Unrealized P&L %": format_percentage(float(h.unrealized_pnl_pct)),
        }
        for h in overview.holdings
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if any(not h.price_is_live for h in overview.holdings):
        st.caption("* Live price unavailable — valued at average buy price.")


# ==========================================================
# Performance tab
# ==========================================================
def _render_performance_tab(user_id: int, overview: VirtualPortfolioOverview) -> None:
    render_section_header("Profit & Loss", icon="📈")

    cols = st.columns(4)
    cols[0].metric("Realized P&L", format_currency(overview.realized_pnl, "₹"))
    cols[1].metric("Unrealized P&L", format_currency(overview.unrealized_pnl, "₹"), delta=format_percentage(float(overview.unrealized_pnl_pct)))
    cols[2].metric("Total P&L", format_currency(overview.total_pnl, "₹"))
    cols[3].metric("Return %", format_percentage(float(overview.return_pct)))

    render_divider()
    render_section_header("Realized P&L Detail", subtitle="Every completed (sold) virtual trade, newest first.", icon="📜")

    realized = trading_service.get_realized_pnl(user_id)
    if not realized.entries:
        render_empty_state("No completed sales yet — realized P&L will appear here once you sell a position.", icon="📜")
        return

    rows = [
        {
            "Ticker": e.ticker,
            "Sold On": format_datetime(e.sell_date),
            "Qty Sold": f"{float(e.quantity_sold):g}",
            "Sell Price": format_currency(e.sell_price, "₹"),
            "Avg. Cost at Sale": format_currency(e.average_cost_at_sale, "₹"),
            "Realized P&L": format_currency(e.realized_pnl, "₹"),
            "Realized P&L %": format_percentage(float(e.realized_pnl_pct)),
        }
        for e in realized.entries
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


# ==========================================================
# Trading Statistics tab
# ==========================================================
def _render_trading_stats_tab(user_id: int) -> None:
    render_section_header("Trading Statistics", subtitle="Based on your completed (sold) virtual trades.", icon="🏆")

    stats = trading_service.get_trading_stats(user_id)
    if stats.completed_trades == 0:
        render_empty_state(
            "You haven't completed any trades yet. Statistics appear here once you sell a position.", icon="🏆"
        )
        st.caption(f"Total orders placed so far: {stats.total_trades} ({stats.buy_trades} buy, {stats.sell_trades} sell).")
        return

    row1 = st.columns(4)
    row1[0].metric("Total Orders", stats.total_trades)
    row1[1].metric("Completed Trades", stats.completed_trades)
    row1[2].metric("Winning Trades", stats.winning_trades)
    row1[3].metric("Losing Trades", stats.losing_trades)

    row2 = st.columns(4)
    row2[0].metric("Win Rate", format_percentage(float(stats.win_rate_pct)))
    row2[1].metric("Total Realized P&L", format_currency(stats.total_realized_pnl, "₹"))
    row2[2].metric("Avg. P&L / Trade", format_currency(stats.average_pnl_per_trade, "₹"))
    row2[3].metric("Breakeven Trades", stats.breakeven_trades)

    render_divider()
    row3 = st.columns(2)
    row3[0].metric("Avg. Profit on Wins", format_currency(stats.average_profit_on_wins, "₹"))
    row3[1].metric("Avg. Loss on Losses", format_currency(stats.average_loss_on_losses, "₹"))


# ==========================================================
# Transactions tab
# ==========================================================
def _render_transactions_tab(user_id: int) -> None:
    render_section_header("Order History", icon="🧾")

    history = trading_service.transaction_history(user_id, page_size=200)
    transactions = history["items"]
    if not transactions:
        render_empty_state("No virtual orders placed yet.", icon="🧾")
        return

    rows = [
        {
            "Date": format_datetime(t.transaction_date),
            "Type": "🟢 BUY" if t.transaction_type == "BUY" else "🔴 SELL",
            "Ticker": t.ticker_symbol,
            "Quantity": f"{float(t.quantity):g}",
            "Price": format_currency(t.price_per_unit, "₹"),
            "Total Amount": format_currency(t.total_amount, "₹"),
            "Cash After": format_currency(t.cash_balance_after, "₹"),
            "Notes": t.notes or "",
        }
        for t in transactions
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if history["total"] > len(transactions):
        st.caption(f"Showing the {len(transactions)} most recent of {history['total']} total orders.")


# ==========================================================
# Main entry point
# ==========================================================
@login_required
def render() -> None:
    """Render the full Virtual Trading page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("🎮 Virtual Trading")
        st.caption("Practice trading with ₹10,00,000 in virtual capital — no real money at risk.")
        render_divider()

        audit_service.log_action(action="VIRTUAL_TRADING_VIEW", user_id=user_id)

        with st.spinner("Loading your virtual portfolio..."):
            overview = trading_service.get_portfolio_overview(user_id)

        _render_kpi_row(overview)
        render_divider()

        tabs = st.tabs(["📈 Trade", "💼 Portfolio", "📊 Performance", "🏆 Trading Statistics", "🧾 Transactions"])
        with tabs[0]:
            _render_trade_tab(user_id)
        with tabs[1]:
            _render_portfolio_tab(overview)
        with tabs[2]:
            _render_performance_tab(user_id, overview)
        with tabs[3]:
            _render_trading_stats_tab(user_id)
        with tabs[4]:
            _render_transactions_tab(user_id)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in virtual trading dashboard: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in virtual trading dashboard: {exc}")
        st.error("An unexpected error occurred while loading Virtual Trading. Please try again.")
