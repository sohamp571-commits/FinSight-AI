"""
virtual_trading/trading_service.py

Purpose: The application-level entry point for virtual BUY/SELL
trades. Does NOT reimplement the atomic buy/sell logic -- that already
exists in `database.virtual_transaction_service` (atomic with
`virtual_accounts` cash and `virtual_holdings` updates). This module
adds the one thing missing at that layer: audit-trail integration,
since `database/*_service.py` files are intentionally Streamlit/session
-free and don't know about the logged-in user's audit context the way
a page-level action does. Mirrors `portfolio/transaction_service.py`
exactly, action names prefixed `VIRTUAL_` instead of `PORTFOLIO_` to
keep the two ledgers distinguishable in the audit log.
"""

from database.audit_service import audit_service
from database.models import VirtualTransaction
from database.virtual_account_service import virtual_account_service as _db_account_service
from database.virtual_holding_service import virtual_holding_service as _db_holding_service
from database.virtual_transaction_service import virtual_transaction_service as _db_transaction_service
from logging_config import logger
from virtual_trading.portfolio_calculator import compute_portfolio_overview
from virtual_trading.realized_pnl import compute_realized_pnl
from virtual_trading.trading_stats import compute_trading_stats

# Re-exported read operations -- no changes needed, so no wrapper required.
transaction_history = _db_transaction_service.transaction_history
search_transactions = _db_transaction_service.search_transactions
get_user_holdings = _db_holding_service.get_user_holdings
get_holding = _db_holding_service.get_holding
portfolio_summary = _db_holding_service.portfolio_summary
current_investment = _db_holding_service.current_investment
get_or_create_account = _db_account_service.get_or_create
get_cash_balance = _db_account_service.get_cash_balance
account_summary = _db_account_service.account_summary

# Calculation/analytics layer -- re-exported the same way as the read
# operations above: these modules already contain the full
# implementation, so `trading_service` is purely a single, stable
# import path for everything virtual-trading-related. No business
# logic is duplicated here.
get_portfolio_overview = compute_portfolio_overview
get_realized_pnl = compute_realized_pnl
get_trading_stats = compute_trading_stats


def buy_stock(
    user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None
) -> VirtualTransaction:
    """Execute a virtual BUY trade and record it in the audit trail."""
    transaction = _db_transaction_service.buy_stock(user_id, ticker_symbol, quantity, price_per_unit, notes)
    audit_service.log_action(
        action="VIRTUAL_BUY",
        user_id=user_id,
        entity_type="virtual_transaction",
        entity_id=transaction.virtual_transaction_id,
        details=f"{ticker_symbol} | qty={quantity} | price={price_per_unit:.2f} | cash_after={transaction.cash_balance_after}",
    )
    logger.info(f"Virtual buy executed: user_id={user_id}, ticker={ticker_symbol}, qty={quantity}")
    return transaction


def sell_stock(
    user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None
) -> VirtualTransaction:
    """Execute a virtual SELL trade and record it in the audit trail."""
    transaction = _db_transaction_service.sell_stock(user_id, ticker_symbol, quantity, price_per_unit, notes)
    audit_service.log_action(
        action="VIRTUAL_SELL",
        user_id=user_id,
        entity_type="virtual_transaction",
        entity_id=transaction.virtual_transaction_id,
        details=f"{ticker_symbol} | qty={quantity} | price={price_per_unit:.2f} | cash_after={transaction.cash_balance_after}",
    )
    logger.info(f"Virtual sell executed: user_id={user_id}, ticker={ticker_symbol}, qty={quantity}")
    return transaction
