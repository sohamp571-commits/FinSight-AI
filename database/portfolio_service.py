"""
database/portfolio_service.py

Purpose: Data-layer service for the `portfolio` table -- a user's
current stock holdings (as opposed to `transactions`, which is the
historical buy/sell ledger). Provides average-cost-basis math for
adding/removing shares and simple valuation summaries.

Note: Live market prices are not available yet (that lands with the
`stock_search` / `analytics` modules in a later phase), so
`portfolio_summary()` accepts an optional `current_prices` dict so
callers can plug in live prices once that service exists, and falls
back to cost-basis valuation when prices aren't supplied.
"""

from typing import Any

from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import Portfolio
from logging_config import logger
from utils import safe_divide, validate_positive_number


class PortfolioService(BaseService[Portfolio]):
    """CRUD and holdings-management operations for the `portfolio` table."""

    model = Portfolio
    pk_column = "portfolio_id"

    # ------------------------------------------------------
    # Create / Add
    # ------------------------------------------------------
    def add_stock(self, user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float) -> Portfolio:
        """
        Add shares of a ticker to a user's portfolio. If the user
        already holds this ticker, blends the new purchase into a
        weighted average buy price; otherwise creates a new holding.
        """
        validate_positive_number(quantity, "quantity")
        validate_positive_number(price_per_unit, "price_per_unit")
        ticker_symbol = ticker_symbol.strip().upper()

        existing = self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol)
        if existing is None:
            new_holding = Portfolio(
                user_id=user_id,
                ticker_symbol=ticker_symbol,
                quantity=quantity,
                average_buy_price=price_per_unit,
            )
            holding = self.create(new_holding)
            logger.info(f"New holding created: user_id={user_id}, ticker={ticker_symbol}")
            return holding

        total_existing_cost = float(existing.quantity) * float(existing.average_buy_price)
        total_new_cost = quantity * price_per_unit
        combined_quantity = float(existing.quantity) + quantity
        new_average_price = safe_divide(total_existing_cost + total_new_cost, combined_quantity)

        updated = self.update(
            existing.portfolio_id, {"quantity": combined_quantity, "average_buy_price": new_average_price}
        )
        logger.info(f"Holding increased: user_id={user_id}, ticker={ticker_symbol}, qty={combined_quantity}")
        return updated

    # ------------------------------------------------------
    # Remove / Reduce
    # ------------------------------------------------------
    def remove_stock(self, user_id: int, ticker_symbol: str, quantity: float) -> Portfolio | None:
        """
        Reduce (or fully remove) a holding. The average buy price is
        left unchanged on a partial sale (standard weighted-average
        cost-basis accounting); the row is deleted entirely once the
        quantity reaches zero.

        Returns:
            The updated Portfolio row, or None if the holding was fully removed.
        """
        validate_positive_number(quantity, "quantity")
        ticker_symbol = ticker_symbol.strip().upper()

        existing = self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol)
        if existing is None:
            raise ValidationError(f"You do not hold any shares of {ticker_symbol}.")
        if quantity > float(existing.quantity):
            raise ValidationError(
                f"Cannot remove {quantity} shares; only {existing.quantity} are held."
            )

        remaining_quantity = float(existing.quantity) - quantity
        if remaining_quantity == 0:
            self.delete(existing.portfolio_id)
            logger.info(f"Holding fully removed: user_id={user_id}, ticker={ticker_symbol}")
            return None

        updated = self.update(existing.portfolio_id, {"quantity": remaining_quantity})
        logger.info(f"Holding reduced: user_id={user_id}, ticker={ticker_symbol}, qty={remaining_quantity}")
        return updated

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def update_holding(self, portfolio_id: int, quantity: float, average_buy_price: float) -> Portfolio:
        """Directly overwrite a holding's quantity and average buy price (e.g. admin correction)."""
        validate_positive_number(quantity, "quantity")
        validate_positive_number(average_buy_price, "average_buy_price")
        return self.update(portfolio_id, {"quantity": quantity, "average_buy_price": average_buy_price})

    # ------------------------------------------------------
    # Read / Reporting
    # ------------------------------------------------------
    def get_user_holdings(self, user_id: int, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """List every holding for a user, sorted by ticker symbol."""
        return self.list(filters={"user_id": user_id}, sort_by="ticker_symbol", page=page, page_size=page_size)

    def current_investment(self, user_id: int) -> float:
        """Return the total cost-basis (quantity * average_buy_price) invested across all holdings."""
        holdings = self.get_user_holdings(user_id, page_size=1000)["items"]
        return sum(float(h.quantity) * float(h.average_buy_price) for h in holdings)

    def portfolio_summary(self, user_id: int, current_prices: dict[str, float] | None = None) -> dict[str, Any]:
        """
        Build a summary of a user's portfolio: per-holding valuation plus
        totals. If `current_prices` (ticker -> live price) is supplied,
        uses it for market value and P&L; otherwise values at cost basis.
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


portfolio_service = PortfolioService()
