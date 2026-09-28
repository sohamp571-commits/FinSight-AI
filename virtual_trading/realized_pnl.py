"""
virtual_trading/realized_pnl.py

Purpose: Computes Realized P&L -- profit/loss actually locked in by
past virtual SELL transactions -- by replaying a user's full virtual
transaction history chronologically per ticker. Requires no schema
change: entirely derived from the existing `virtual_transactions`
table (Phase 13), mirroring `portfolio/realized_pnl.py` (the real
-money equivalent) algorithm-for-algorithm, since `average_buy_price`
on `virtual_holdings` is only ever updated on BUY (weighted-average
cost basis; confirmed unchanged on SELL in
`database.virtual_transaction_service.sell_stock`). That means the
average cost basis at the exact moment of each historical virtual sale
can be reconstructed precisely by replaying transactions in order.

Differs from `portfolio/realized_pnl.py` in exactly one way: this
version works in `Decimal` throughout (via `decimal_utils.py`) rather
than `float`, per Batch 13's requirement that virtual trading
calculations avoid floating-point rounding error for monetary figures.

Distinct from Unrealized P&L (`portfolio_calculator.compute_portfolio_overview`,
this package), which reflects only currently-held positions marked to
market -- this module only ever looks at transactions that have
already happened.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from database.virtual_transaction_service import virtual_transaction_service
from virtual_trading.decimal_utils import ZERO, quantize_money, quantize_percent, quantize_quantity, safe_divide_decimal, to_decimal


@dataclass
class RealizedSaleEntry:
    """A single historical virtual SELL event and the profit/loss it locked in."""

    ticker: str
    sell_date: datetime
    quantity_sold: Decimal
    sell_price: Decimal
    average_cost_at_sale: Decimal
    realized_pnl: Decimal
    realized_pnl_pct: Decimal
    virtual_transaction_id: int  # tiebreaker for deterministic ordering when sell_date values collide (see below)


@dataclass
class RealizedPnLReport:
    """Full realized P&L report: total, per-sale detail, and per-ticker rollup."""

    total_realized_pnl: Decimal
    entries: list[RealizedSaleEntry]
    by_ticker: dict[str, Decimal]


def compute_realized_pnl(user_id: int) -> RealizedPnLReport:
    """
    Replay every virtual BUY/SELL transaction in chronological order
    (per ticker) to compute Realized P&L for each historical virtual
    sale.

    Algorithm (weighted-average cost basis, matching the exact
    behavior of `database.virtual_transaction_service.buy_stock`/
    `sell_stock`):
        - On BUY: blend the new purchase into the running weighted
          average cost; increase running quantity.
        - On SELL: realized P&L for that sale = (sell_price -
          running_average_cost) * quantity_sold. The average cost is
          left unchanged (mirrors the DB's own partial-sale behavior);
          only the running quantity decreases.

    Deterministic and based only on the user's own virtual transaction
    history -- no live market data is involved.
    """
    all_transactions = virtual_transaction_service.transaction_history(user_id, page_size=5000)["items"]

    transactions_by_ticker: dict[str, list] = {}
    for txn in all_transactions:
        transactions_by_ticker.setdefault(txn.ticker_symbol, []).append(txn)

    entries: list[RealizedSaleEntry] = []
    total_realized = ZERO
    per_ticker_totals: dict[str, Decimal] = {}

    for ticker, txns in transactions_by_ticker.items():
        # Chronological order is essential: weighted-average cost basis
        # depends on every prior BUY having already been folded in.
        # `transaction_date` alone is not a safe sort key here: it's a
        # plain MySQL DATETIME column (second precision, not
        # DATETIME(6)), so trades executed within the same second land
        # on an identical stored timestamp and MySQL does not guarantee
        # a stable tie-break order when queried back. `virtual_transaction_id`
        # (auto-increment primary key) is added as a tiebreaker since it
        # always reflects true insertion order regardless of timestamp
        # precision, without requiring any schema change.
        ordered_txns = sorted(txns, key=lambda t: (t.transaction_date, t.virtual_transaction_id))
        running_quantity = ZERO
        running_average_cost = ZERO

        for txn in ordered_txns:
            quantity = to_decimal(txn.quantity)
            price = to_decimal(txn.price_per_unit)

            if txn.transaction_type == "BUY":
                new_quantity = running_quantity + quantity
                running_average_cost = (
                    safe_divide_decimal(running_quantity * running_average_cost + quantity * price, new_quantity)
                    if new_quantity
                    else ZERO
                )
                running_quantity = new_quantity
            else:  # SELL
                realized_pnl = (price - running_average_cost) * quantity
                realized_pnl_pct = (
                    safe_divide_decimal(realized_pnl, running_average_cost * quantity) * 100
                    if running_average_cost
                    else ZERO
                )
                entries.append(
                    RealizedSaleEntry(
                        ticker=ticker,
                        sell_date=txn.transaction_date,
                        quantity_sold=quantize_quantity(quantity),
                        sell_price=quantize_money(price),
                        average_cost_at_sale=quantize_money(running_average_cost),
                        realized_pnl=quantize_money(realized_pnl),
                        realized_pnl_pct=quantize_percent(realized_pnl_pct),
                        virtual_transaction_id=txn.virtual_transaction_id,
                    )
                )
                total_realized += realized_pnl
                per_ticker_totals[ticker] = per_ticker_totals.get(ticker, ZERO) + realized_pnl
                running_quantity -= quantity
                # running_average_cost intentionally unchanged on SELL,
                # matching database.virtual_transaction_service.sell_stock exactly.

    # Newest-first for display; `virtual_transaction_id` breaks ties
    # between sales whose stored `transaction_date` collides at
    # second-level precision (see the sort above for why).
    entries.sort(key=lambda e: (e.sell_date, e.virtual_transaction_id), reverse=True)

    return RealizedPnLReport(
        total_realized_pnl=quantize_money(total_realized),
        entries=entries,
        by_ticker={ticker: quantize_money(total) for ticker, total in per_ticker_totals.items()},
    )
