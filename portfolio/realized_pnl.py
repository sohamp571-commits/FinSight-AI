"""
portfolio/realized_pnl.py

Purpose: Computes Realized P&L -- profit/loss actually locked in by
past SELL transactions -- by replaying a user's full transaction
history chronologically per ticker. Requires NO schema change and NO
new table: entirely derived from the existing `transactions` table
(Phase 1/3), since `average_buy_price` is only ever updated on BUY
transactions (weighted-average cost basis; confirmed unchanged on
SELL in `database.transaction_service.sell_stock`). That means the
average cost basis at the exact moment of each historical sale can be
reconstructed precisely by replaying transactions in order.

Distinct from the existing "Unrealized P&L" already shown on the
Portfolio Overview tab (`portfolio_calculator.compute_portfolio_overview`),
which reflects only currently-held positions marked to live market price.
"""

from dataclasses import dataclass
from datetime import datetime

from portfolio.transaction_service import transaction_history
from utils import safe_divide


@dataclass
class RealizedSaleEntry:
    """A single historical SELL event and the profit/loss it locked in."""

    ticker: str
    sell_date: datetime
    quantity_sold: float
    sell_price: float
    average_cost_at_sale: float
    realized_pnl: float
    realized_pnl_pct: float


@dataclass
class RealizedPnLReport:
    """Full realized P&L report: total, per-sale detail, and per-ticker rollup."""

    total_realized_pnl: float
    entries: list[RealizedSaleEntry]
    by_ticker: dict[str, float]


def compute_realized_pnl(user_id: int) -> RealizedPnLReport:
    """
    Replay every BUY/SELL transaction in chronological order (per
    ticker) to compute Realized P&L for each historical sale.

    Algorithm (weighted-average cost basis, matching the exact
    behavior of `database.transaction_service.buy_stock`/`sell_stock`):
        - On BUY: blend the new purchase into the running weighted
          average cost; increase running quantity.
        - On SELL: realized P&L for that sale = (sell_price -
          running_average_cost) * quantity_sold. The average cost is
          left unchanged (mirrors the DB's own partial-sale behavior);
          only the running quantity decreases.
    """
    all_transactions = transaction_history(user_id, page_size=5000)["items"]

    transactions_by_ticker: dict[str, list] = {}
    for txn in all_transactions:
        transactions_by_ticker.setdefault(txn.ticker_symbol, []).append(txn)

    entries: list[RealizedSaleEntry] = []
    total_realized = 0.0
    per_ticker_totals: dict[str, float] = {}

    for ticker, txns in transactions_by_ticker.items():
        ordered_txns = sorted(txns, key=lambda t: t.transaction_date)
        running_quantity = 0.0
        running_average_cost = 0.0

        for txn in ordered_txns:
            quantity = float(txn.quantity)
            price = float(txn.price_per_unit)

            if txn.transaction_type == "BUY":
                new_quantity = running_quantity + quantity
                running_average_cost = (
                    safe_divide(running_quantity * running_average_cost + quantity * price, new_quantity)
                    if new_quantity
                    else 0.0
                )
                running_quantity = new_quantity
            else:  # SELL
                realized_pnl = (price - running_average_cost) * quantity
                realized_pnl_pct = (
                    safe_divide(realized_pnl, running_average_cost * quantity) * 100
                    if running_average_cost
                    else 0.0
                )
                entries.append(
                    RealizedSaleEntry(
                        ticker=ticker,
                        sell_date=txn.transaction_date,
                        quantity_sold=quantity,
                        sell_price=price,
                        average_cost_at_sale=round(running_average_cost, 4),
                        realized_pnl=round(realized_pnl, 2),
                        realized_pnl_pct=round(realized_pnl_pct, 2),
                    )
                )
                total_realized += realized_pnl
                per_ticker_totals[ticker] = per_ticker_totals.get(ticker, 0.0) + realized_pnl
                running_quantity -= quantity
                # running_average_cost intentionally unchanged on SELL,
                # matching database.transaction_service.sell_stock exactly.

    entries.sort(key=lambda e: e.sell_date, reverse=True)

    return RealizedPnLReport(
        total_realized_pnl=round(total_realized, 2),
        entries=entries,
        by_ticker={ticker: round(total, 2) for ticker, total in per_ticker_totals.items()},
    )