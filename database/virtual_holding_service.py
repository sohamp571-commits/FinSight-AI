"""
database/virtual_holding_service.py

Purpose: Data-layer service for the `virtual_holdings` table -- a
user's current paper-trading positions (as opposed to
`virtual_transactions`, which is the historical BUY/SELL ledger).
Mirrors `database/portfolio_service.py` exactly (same weighted
average-cost-basis math, same method names/shapes) so the two are a
drop-in match for anyone already familiar with the real portfolio
service; the only difference is the table/model and that this one is
virtual (paper) money, not real trades.
"""

from typing import Any

from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import VirtualHolding
from logging_config import logger
from utils import safe_divide, validate_positive_number


class VirtualHoldingService(BaseService[VirtualHolding]):
    """CRUD and holdings-management operations for the `virtual_holdings` table."""

    model = VirtualHolding
    pk_column = "virtual_holding_id"

    # ------------------------------------------------------
    # Create / Add
    # ------------------------------------------------------
    def add_stock(self, user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float) -> VirtualHolding:
        """
        Add shares of a ticker to a user's virtual holdings. If the
        user already holds this ticker, blends the new purchase into a
        weighted average buy price (respecting the DB-level
        UNIQUE(user_id, ticker_symbol) constraint); otherwise creates a
        new holding row.
        """
        validate_positive_number(quantity, "quantity")
        validate_positive_number(price_per_unit, "price_per_unit")
        ticker_symbol = ticker_symbol.strip().upper()

        existing = self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol)
        if existing is None:
            new_holding = VirtualHolding(
                user_id=user_id,
                ticker_symbol=ticker_symbol,
                quantity=quantity,
                average_buy_price=price_per_unit,
            )
            holding = self.create(new_holding)
            logger.info(f"New virtual holding created: user_id={user_id}, ticker={ticker_symbol}")
            return holding

        total_existing_cost = float(existing.quantity) * float(existing.average_buy_price)
        total_new_cost = quantity * price_per_unit
        combined_quantity = float(existing.quantity) + quantity
        new_average_price = safe_divide(total_existing_cost + total_new_cost, combined_quantity)

        updated = self.update(
            existing.virtual_holding_id, {"quantity": combined_quantity, "average_buy_price": new_average_price}
        )
        logger.info(f"Virtual holding increased: user_id={user_id}, ticker={ticker_symbol}, qty={combined_quantity}")
        return updated

    # ------------------------------------------------------
    # Remove / Reduce
    # ------------------------------------------------------
    def remove_stock(self, user_id: int, ticker_symbol: str, quantity: float) -> VirtualHolding | None:
        """
        Reduce (or fully remove) a virtual holding. The average buy
        price is left unchanged on a partial sale (standard
        weighted-average cost-basis accounting); the row is deleted
        entirely once the quantity reaches zero.

        Returns:
            The updated VirtualHolding row, or None if the holding was fully removed.
        """
        validate_positive_number(quantity, "quantity")
        ticker_symbol = ticker_symbol.strip().upper()

        existing = self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol)
        if existing is None:
            raise ValidationError(f"You do not hold any virtual shares of {ticker_symbol}.")
        if quantity > float(existing.quantity):
            raise ValidationError(
                f"Cannot sell {quantity} shares; only {existing.quantity} are held in your virtual account."
            )

        remaining_quantity = float(existing.quantity) - quantity
        if remaining_quantity == 0:
            self.delete(existing.virtual_holding_id)
            logger.info(f"Virtual holding fully removed: user_id={user_id}, ticker={ticker_symbol}")
            return None

        updated = self.update(existing.virtual_holding_id, {"quantity": remaining_quantity})
        logger.info(f"Virtual holding reduced: user_id={user_id}, ticker={ticker_symbol}, qty={remaining_quantity}")
        return updated

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def update_holding(self, virtual_holding_id: int, quantity: float, average_buy_price: float) -> VirtualHolding:
        """Directly overwrite a holding's quantity and average buy price (e.g. admin correction)."""
        validate_positive_number(quantity, "quantity")
        validate_positive_number(average_buy_price, "average_buy_price")
        return self.update(virtual_holding_id, {"quantity": quantity, "average_buy_price": average_buy_price})

    # ------------------------------------------------------
    # Read / Reporting
    # ------------------------------------------------------
    def get_user_holdings(self, user_id: int, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """List every virtual holding for a user, sorted by ticker symbol."""
        return self.list(filters={"user_id": user_id}, sort_by="ticker_symbol", page=page, page_size=page_size)

    def get_holding(self, user_id: int, ticker_symbol: str) -> VirtualHolding | None:
        """Fetch a single virtual holding for a user + ticker, or None if not held."""
        return self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol.strip().upper())

    def current_investment(self, user_id: int) -> float:
        """Return the total cost-basis (quantity * average_buy_price) invested across all virtual holdings."""
        holdings = self.get_user_holdings(user_id, page_size=1000)["items"]
        return sum(float(h.quantity) * float(h.average_buy_price) for h in holdings)

    def portfolio_summary(self, user_id: int, current_prices: dict[str, float] | None = None) -> dict[str, Any]:
        """
        Build a summary of a user's virtual portfolio: per-holding
        valuation plus totals. If `current_prices` (ticker -> live
        price) is supplied, uses it for market value and unrealized
        P&L; otherwise values at cost basis. Mirrors
        `PortfolioService.portfolio_summary` exactly.
        """
        current_prices = current_prices or {}
        holdings = self.get_user_holdings(user_id, page_size=1000)["items"]

        rows = []
        total_invested = 0.0
        total_current_value = 0.0

        for holding in holdings:
            invested = float(holding.quantity) * float(holding.average_buy_price)
            market_price = current_prices.get(holding.ticker_symbol, float(holding.average_buy_price))
            current_value = float(holding.quantity) * market_price
            profit_loss = current_value - invested
            profit_loss_pct = safe_divide(profit_loss, invested) * 100

            rows.append(
                {
                    "ticker_symbol": holding.ticker_symbol,
                    "quantity": float(holding.quantity),
                    "average_buy_price": float(holding.average_buy_price),
                    "current_price": market_price,
                    "invested_value": invested,
                    "current_value": current_value,
                    "profit_loss": profit_loss,
                    "profit_loss_pct": profit_loss_pct,
                }
            )
            total_invested += invested
            total_current_value += current_value

        return {
            "holdings": rows,
            "total_invested": total_invested,
            "total_current_value": total_current_value,
            "total_profit_loss": total_current_value - total_invested,
            "total_profit_loss_pct": safe_divide(total_current_value - total_invested, total_invested) * 100,
        }


virtual_holding_service = VirtualHoldingService()
