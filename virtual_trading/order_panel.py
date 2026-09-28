"""
virtual_trading/order_panel.py

Purpose: The BUY/SELL order entry UI for Virtual Trading. Deliberately
a two-step flow -- unlike the real portfolio's single-step transaction
form in `portfolio/portfolio_dashboard.py` (`_render_transaction_form`)
-- because a paper-trading order panel is expected to feel like a
professional trading platform, where you review an order before it's
sent. Concretely:

    1. Reactive entry widgets (ticker, side, quantity, price) update a
       live *preview* only -- typing/selecting never touches the
       database.
    2. "Review Order" validates the input and stores a pending order
       in `st.session_state["vt_pending_order"]` -- still no database
       write.
    3. Only "Confirm & Execute" on the review card actually calls
       `virtual_trading.trading_service.buy_stock`/`sell_stock`.

This module never reimplements BUY/SELL business logic: cash/holding
validation, cost-basis math, and the atomic database write all remain
entirely inside `database.virtual_transaction_service` (via
`trading_service`), exactly as built and tested in Batch 2. The soft
checks here (cash/holdings previews, ticker syntax) exist purely to
give the user fast feedback -- `trading_service.buy_stock`/`sell_stock`
remains the sole source of truth and will reject anything that slips
past them.
"""

import streamlit as st

from custom_exceptions import FinSightBaseException, RecordNotFoundError, ValidationError
from dashboard.dashboard_layout import render_divider, render_section_header
from helper import format_currency
from logging_config import logger
from stock_search.search_service import resolve_ticker
from utils import is_valid_ticker
from virtual_trading import trading_service
from virtual_trading.decimal_utils import to_decimal

_PENDING_ORDER_KEY = "vt_pending_order"
_QUERY_KEY = "vt_order_query"
_SIDE_KEY = "vt_order_side"
_QTY_KEY = "vt_order_qty"
_PRICE_KEY = "vt_order_price"


def _reset_order_form() -> None:
    """Clear the entry widgets after a successful trade, so the form starts fresh."""
    for key in (_QUERY_KEY, _QTY_KEY, _PRICE_KEY):
        st.session_state.pop(key, None)


def _render_price_chart(ticker: str) -> None:
    """
    Optional price-chart preview for the ticker currently being
    traded, reusing the exact same candlestick component Technical
    Analysis uses. Purely cosmetic -- if price history can't be
    fetched (e.g. no network access to the market-data provider), the
    expander just shows a short message instead of failing the page.
    """
    with st.expander(f"📈 View {ticker} Price Chart", expanded=False):
        try:
            from dashboard.market_data_service import fetch_price_history
            from analytics.candlestick_chart import build_candlestick_chart
            from dashboard.chart_helpers import CHART_CONFIG

            history_df = fetch_price_history(ticker, period="3mo", interval="1d")
            if history_df is None or history_df.empty:
                st.caption("Price chart unavailable right now.")
                return
            fig = build_candlestick_chart(history_df, ticker)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key=f"vt_chart_{ticker}")
        except Exception as exc:  # noqa: BLE001 - a broken chart must never block placing an order
            logger.warning(f"Virtual trading price chart unavailable for {ticker}: {exc}")
            st.caption("Price chart unavailable right now.")


def _validate_and_stage_order(
    user_id: int, query: str, side: str, quantity: float, price: float, resolved_ticker: str | None, quote_is_live: bool
) -> None:
    """
    Validate the order the user is about to place and, if everything
    checks out, stage it in session state for the confirmation step.
    Never calls buy_stock/sell_stock directly -- staging only.
    """
    if not query.strip():
        st.warning("Enter a ticker symbol or company name.")
        return

    try:
        ticker = resolved_ticker or resolve_ticker(query)
    except ValidationError as exc:
        st.error(exc.message)
        return

    if not is_valid_ticker(ticker):
        st.error(f"'{ticker}' is not a valid ticker symbol.")
        return

    if quantity <= 0:
        st.warning("Quantity must be greater than zero.")
        return

    if price <= 0:
        st.warning(
            "Enter an execution price greater than zero."
            if not quote_is_live
            else "Price must be greater than zero."
        )
        return

    if side == "SELL":
        holding = trading_service.get_holding(user_id, ticker)
        held_qty = float(holding.quantity) if holding is not None else 0.0
        if quantity > held_qty:
            st.error(f"You only hold {held_qty:g} shares of {ticker}; cannot sell {quantity:g}.")
            return
    else:
        cash_balance = trading_service.get_cash_balance(user_id)
        estimated_total = quantity * price
        if estimated_total > cash_balance:
            st.error(
                f"Insufficient virtual cash: balance is {format_currency(cash_balance, '₹')}, "
                f"this order requires {format_currency(estimated_total, '₹')}."
            )
            return

    st.session_state[_PENDING_ORDER_KEY] = {
        "user_id": user_id,
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "quote_is_live": quote_is_live,
    }


def _execute_pending_order(user_id: int, pending: dict) -> None:
    """Execute a staged order via the existing, already-tested trading_service BUY/SELL functions."""
    try:
        if pending["side"] == "BUY":
            transaction = trading_service.buy_stock(user_id, pending["ticker"], pending["quantity"], pending["price"])
            st.success(
                f"✅ Bought {pending['quantity']:g} shares of {pending['ticker']} at "
                f"{format_currency(pending['price'], '₹')}. New cash balance: "
                f"{format_currency(transaction.cash_balance_after, '₹')}."
            )
        else:
            transaction = trading_service.sell_stock(user_id, pending["ticker"], pending["quantity"], pending["price"])
            st.success(
                f"✅ Sold {pending['quantity']:g} shares of {pending['ticker']} at "
                f"{format_currency(pending['price'], '₹')}. New cash balance: "
                f"{format_currency(transaction.cash_balance_after, '₹')}."
            )
        st.session_state.pop(_PENDING_ORDER_KEY, None)
        _reset_order_form()
        st.rerun()
    except ValidationError as exc:
        # e.g. cash/holdings changed between staging and confirming (another
        # session, or a soft check here missed an edge case) -- the atomic
        # service is the final authority and correctly rejected the trade.
        st.warning(exc.message)
    except RecordNotFoundError as exc:
        st.error(exc.message)
    except FinSightBaseException as exc:
        logger.error(f"Virtual order execution failed: {exc}")
        st.error(exc.message)
    except Exception as exc:  # noqa: BLE001 - last line of defense for this widget
        logger.exception(f"Unexpected error executing virtual order: {exc}")
        st.error("An unexpected error occurred while executing your order. Please try again.")


def _render_pending_order_confirmation(user_id: int) -> None:
    """Render the Review/Confirm card for a staged order, if one exists for this user."""
    pending = st.session_state.get(_PENDING_ORDER_KEY)
    if not pending or pending.get("user_id") != user_id:
        return

    render_divider()
    render_section_header("Review Your Order", icon="🧾")

    quantity_dec = to_decimal(pending["quantity"])
    price_dec = to_decimal(pending["price"])
    estimated_total = quantity_dec * price_dec

    side_label = "🟢 BUY" if pending["side"] == "BUY" else "🔴 SELL"
    col1, col2, col3 = st.columns(3)
    col1.metric("Order", f"{side_label} {pending['ticker']}")
    col2.metric("Quantity", f"{pending['quantity']:g} shares")
    col3.metric("Estimated Total", format_currency(estimated_total, "₹"))
    st.caption(f"Execution price: {format_currency(price_dec, '₹')}" + ("" if pending["quote_is_live"] else " (manually entered — live market data was unavailable)"))

    if pending["side"] == "BUY":
        cash_balance = to_decimal(trading_service.get_cash_balance(user_id))
        projected_cash = cash_balance - estimated_total
        st.caption(f"Projected cash balance after this order: **{format_currency(projected_cash, '₹')}**")
    else:
        holding = trading_service.get_holding(user_id, pending["ticker"])
        held_qty = to_decimal(holding.quantity) if holding is not None else to_decimal(0)
        projected_qty = held_qty - quantity_dec
        st.caption(f"Projected remaining {pending['ticker']} position: **{float(projected_qty):g} shares**")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        confirm_clicked = st.button(
            "✅ Confirm & Execute", use_container_width=True, key="vt_confirm_order_btn", type="primary"
        )
    with col_cancel:
        cancel_clicked = st.button("✖️ Cancel", use_container_width=True, key="vt_cancel_order_btn")

    if cancel_clicked:
        st.session_state.pop(_PENDING_ORDER_KEY, None)
        st.rerun()

    if confirm_clicked:
        _execute_pending_order(user_id, pending)


def render_order_panel(user_id: int) -> None:
    """Render the full order entry + review/confirm workflow for a user's virtual account."""
    render_section_header(
        "Place a Virtual Order", subtitle="Trade with your virtual balance — no real money involved.", icon="🎯"
    )

    cash_balance = trading_service.get_cash_balance(user_id)
    st.caption(f"💵 Available virtual cash: **{format_currency(cash_balance, '₹')}**")

    col_query, col_side, col_qty = st.columns([2, 1, 1])
    with col_query:
        query = st.text_input("Ticker / Company", placeholder="e.g. RELIANCE, TCS, INFY", key=_QUERY_KEY)
    with col_side:
        side = st.selectbox("Side", ["BUY", "SELL"], key=_SIDE_KEY)
    with col_qty:
        quantity = st.number_input("Quantity", min_value=0.0, step=1.0, key=_QTY_KEY)

    resolved_ticker: str | None = None
    quote = None
    if query.strip():
        try:
            resolved_ticker = resolve_ticker(query)
        except ValidationError:
            resolved_ticker = None

        if resolved_ticker:
            from dashboard.market_data_service import fetch_quote

            quote = fetch_quote(resolved_ticker)

    if resolved_ticker:
        if quote is not None:
            direction_icon = "🟢" if quote["change"] >= 0 else "🔴"
            st.info(
                f"**{resolved_ticker}** — Current Price: {format_currency(quote['price'], '₹')}  "
                f"{direction_icon} {quote['change']:+.2f} ({quote['change_pct']:+.2f}%)"
            )
        else:
            st.warning(
                f"⚠️ Live market price for **{resolved_ticker}** is currently unavailable "
                "(market data provider unreachable, or this ticker doesn't exist). "
                "You can still enter a price manually below to simulate a trade."
            )

        if side == "SELL":
            holding = trading_service.get_holding(user_id, resolved_ticker)
            held_qty = float(holding.quantity) if holding is not None else 0.0
            st.caption(f"📦 You currently hold **{held_qty:g}** shares of {resolved_ticker}.")

        _render_price_chart(resolved_ticker)

    default_price = float(quote["price"]) if quote is not None else 0.0
    price = st.number_input(
        "Execution Price (₹)",
        min_value=0.0,
        step=0.05,
        value=default_price,
        key=_PRICE_KEY,
        help="Defaults to the live market price when available. Edit to simulate a limit order, "
        "or to place an order when live data is unavailable.",
    )

    if st.button("🔍 Review Order", use_container_width=True, key="vt_review_order_btn"):
        _validate_and_stage_order(user_id, query, side, quantity, price, resolved_ticker, quote_is_live=quote is not None)

    _render_pending_order_confirmation(user_id)
