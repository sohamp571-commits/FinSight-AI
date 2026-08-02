"""
portfolio/transaction_service.py

Purpose: The application-level entry point for buy/sell transactions.
Does NOT reimplement the atomic buy/sell logic -- that already exists
in `database.transaction_service` (Phase 3, the `transactions` table,
already atomic with `portfolio` updates). This module adds the one
thing missing at that layer: audit-trail integration, since
`database/*_service.py` files are intentionally Streamlit/session-free
and don't know about the logged-in user's audit context the way a
page-level action does.
"""

from database.audit_service import audit_service
from database.models import Transaction
from database.transaction_service import transaction_service as _db_transaction_service
from logging_config import logger

# Re-exported read operations -- no changes needed, so no wrapper required.
transaction_history = _db_transaction_service.transaction_history
search_transactions = _db_transaction_service.search_transactions


def buy_stock(user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None) -> Transaction:
    """Execute a BUY transaction and record it in the audit trail."""
    transaction = _db_transaction_service.buy_stock(user_id, ticker_symbol, quantity, price_per_unit, notes)
    audit_service.log_action(
        action="PORTFOLIO_BUY",
        user_id=user_id,
        entity_type="transaction",
        entity_id=transaction.transaction_id,
        details=f"{ticker_symbol} | qty={quantity} | price={price_per_unit:.2f}",
    )
    logger.info(f"Buy executed via portfolio module: user_id={user_id}, ticker={ticker_symbol}, qty={quantity}")
    return transaction


def sell_stock(user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None) -> Transaction:
    """Execute a SELL transaction and record it in the audit trail."""
    transaction = _db_transaction_service.sell_stock(user_id, ticker_symbol, quantity, price_per_unit, notes)
    audit_service.log_action(
        action="PORTFOLIO_SELL",
        user_id=user_id,
        entity_type="transaction",
        entity_id=transaction.transaction_id,
        details=f"{ticker_symbol} | qty={quantity} | price={price_per_unit:.2f}",
    )
    logger.info(f"Sell executed via portfolio module: user_id={user_id}, ticker={ticker_symbol}, qty={quantity}")
    return transaction
