"""
virtual_trading package

Phase 13 -- Virtual Trading / Paper Trading for FinSight AI.

New database tables: `virtual_accounts`, `virtual_holdings`,
`virtual_transactions` (see `database/migration_phase13.sql`), each
mirroring the shape of the real `portfolio`/`transactions` tables but
kept fully separate so real and paper-trading data can never mix.

Sub-modules:
    decimal_utils.py       - shared Decimal-precision helpers for the calculation layer
    realized_pnl.py         - Decimal-precision chronological BUY/SELL replay (virtual-only;
                              distinct from, and does not import, portfolio.realized_pnl)
    portfolio_calculator.py  - portfolio overview: cash, invested/current value,
                               unrealized/realized/today's/total P&L, return %
    trading_stats.py          - win/loss trading statistics derived from realized_pnl.py
    trading_service.py         - application-level BUY/SELL entry point + read-only
                                  facade over the calculation layer: facade over
                                  database.virtual_transaction_service + audit logging
                                  (mirrors portfolio/transaction_service.py)
    order_panel.py               - BUY/SELL order entry UI (review/confirm workflow)
    trading_dashboard.py          - main controller (entry point: trading_dashboard.render)

Data-layer services this package builds on (in `database/`):
    virtual_account_service.py      - virtual_accounts CRUD + cash balance ops
    virtual_holding_service.py      - virtual_holdings CRUD + weighted-avg cost basis
    virtual_transaction_service.py  - atomic BUY/SELL across all three virtual tables
"""

from virtual_trading.trading_dashboard import render

__all__ = ["render"]
