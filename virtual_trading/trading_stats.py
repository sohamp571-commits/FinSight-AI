"""
virtual_trading/trading_stats.py

Purpose: Aggregate trading-performance statistics derived from a
user's Realized P&L replay (`realized_pnl.py`, this package).

Definition of a "completed trade": one historical SELL event, i.e. one
`RealizedSaleEntry` from `realized_pnl.compute_realized_pnl`. Every
SELL locks in exactly one realized result, so completed-trade
statistics are computed directly from that report rather than
re-deriving anything from raw transactions. A currently-held (never
sold) position is never counted as a completed trade here -- it only
ever shows up as `unrealized_pnl` in
`portfolio_calculator.compute_portfolio_overview`, keeping "trades I
actually finished" and "positions still open" from being mixed
together in these statistics.
"""

from dataclasses import dataclass
from decimal import Decimal

from database.virtual_transaction_service import virtual_transaction_service
from virtual_trading.decimal_utils import ZERO, quantize_money, quantize_percent, safe_divide_decimal, to_decimal
from virtual_trading.realized_pnl import RealizedPnLReport, compute_realized_pnl


@dataclass
class TradingStatistics:
    """Win/loss performance statistics for a user's completed (sold) virtual trades."""

    total_trades: int  # every virtual_transactions row (BUY + SELL)
    buy_trades: int
    sell_trades: int
    completed_trades: int  # == sell_trades; every SELL locks in exactly one realized result
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate_pct: Decimal
    total_realized_pnl: Decimal
    average_pnl_per_trade: Decimal
    average_profit_on_wins: Decimal
    average_loss_on_losses: Decimal


def compute_trading_stats(user_id: int, realized_report: RealizedPnLReport | None = None) -> TradingStatistics:
    """
    Compute win/loss trading statistics for a user's virtual trading
    history.

    Args:
        user_id: whose virtual transaction history to analyze.
        realized_report: optional pre-computed `RealizedPnLReport` to
            reuse (e.g. a caller that already called
            `compute_realized_pnl` for the same user in the same
            request, such as `portfolio_calculator.compute_portfolio_overview`,
            can pass it in here instead of triggering a second replay
            of the same transaction history).

    Handles zero trades safely: every rate/average is 0, not a
    division-by-zero error.
    """
    all_transactions = virtual_transaction_service.transaction_history(user_id, page_size=5000)["items"]
    buy_trades = sum(1 for t in all_transactions if t.transaction_type == "BUY")
    sell_trades = sum(1 for t in all_transactions if t.transaction_type == "SELL")
    total_trades = len(all_transactions)

    report = realized_report if realized_report is not None else compute_realized_pnl(user_id)
    completed = report.entries  # one entry per SELL == one completed trade

    winners = [e for e in completed if e.realized_pnl > 0]
    losers = [e for e in completed if e.realized_pnl < 0]
    breakeven = [e for e in completed if e.realized_pnl == 0]
    completed_count = len(completed)

    win_rate_pct = (
        safe_divide_decimal(to_decimal(len(winners)), to_decimal(completed_count)) * 100 if completed_count else ZERO
    )
    average_pnl_per_trade = (
        safe_divide_decimal(report.total_realized_pnl, to_decimal(completed_count)) if completed_count else ZERO
    )
    average_profit_on_wins = (
        safe_divide_decimal(sum((e.realized_pnl for e in winners), ZERO), to_decimal(len(winners)))
        if winners
        else ZERO
    )
    average_loss_on_losses = (
        safe_divide_decimal(sum((e.realized_pnl for e in losers), ZERO), to_decimal(len(losers)))
        if losers
        else ZERO
    )

    return TradingStatistics(
        total_trades=total_trades,
        buy_trades=buy_trades,
        sell_trades=sell_trades,
        completed_trades=completed_count,
        winning_trades=len(winners),
        losing_trades=len(losers),
        breakeven_trades=len(breakeven),
        win_rate_pct=quantize_percent(win_rate_pct),
        total_realized_pnl=quantize_money(report.total_realized_pnl),
        average_pnl_per_trade=quantize_money(average_pnl_per_trade),
        average_profit_on_wins=quantize_money(average_profit_on_wins),
        average_loss_on_losses=quantize_money(average_loss_on_losses),
    )
