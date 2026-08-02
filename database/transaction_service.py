"""
database/transaction_service.py

Purpose: Data-layer service for the `transactions` table -- the
permanent, append-only buy/sell ledger. Buying or selling a stock must
also update the corresponding `portfolio` row; to guarantee both
writes succeed or fail together, `buy_stock`/`sell_stock` use a single
explicit session (via crud.py) rather than delegating to
PortfolioService (which would open a second, independent transaction).
"""

from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from constants import TransactionType
from custom_exceptions import DatabaseQueryError, ValidationError
from database import crud
from database.base_service import BaseService
from database.connection import db_connection
from database.models import Portfolio, Transaction
from logging_config import logger
from utils import safe_divide, validate_positive_number


class TransactionService(BaseService[Transaction]):
    """CRUD and buy/sell operations for the `transactions` table."""

    model = Transaction
    pk_column = "transaction_id"

    # ------------------------------------------------------
    # Buy / Sell (atomic with portfolio update)
    # ------------------------------------------------------
    def buy_stock(
        self, user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None
    ) -> Transaction:
        """Record a BUY transaction and increase the matching portfolio holding atomically."""
        validate_positive_number(quantity, "quantity")
        validate_positive_number(price_per_unit, "price_per_unit")
        ticker_symbol = ticker_symbol.strip().upper()
        total_amount = quantity * price_per_unit

        try:
            with db_connection.get_session() as session:
                transaction = crud.create(
                    session,
                    Transaction(
                        user_id=user_id,
                        ticker_symbol=ticker_symbol,
                        transaction_type=TransactionType.BUY.value,
                        quantity=quantity,
                        price_per_unit=price_per_unit,
                        total_amount=total_amount,
                        transaction_date=datetime.utcnow(),
                        notes=notes,
                    ),
                )

                existing_holding = crud.get_one_by(session, Portfolio, user_id=user_id, ticker_symbol=ticker_symbol)
                if existing_holding is None:
                    crud.create(
                        session,
                        Portfolio(
                            user_id=user_id,
                            ticker_symbol=ticker_symbol,
                            quantity=quantity,
                            average_buy_price=price_per_unit,
                        ),
                    )
                else:
                    total_existing_cost = float(existing_holding.quantity) * float(existing_holding.average_buy_price)
                    combined_quantity = float(existing_holding.quantity) + quantity
                    new_average_price = safe_divide(total_existing_cost + total_amount, combined_quantity)
                    crud.update_by_id(
                        session,
                        Portfolio,
                        existing_holding.portfolio_id,
                        "portfolio_id",
                        {"quantity": combined_quantity, "average_buy_price": new_average_price},
                    )

                session.expunge(transaction)
                logger.info(f"BUY recorded: user_id={user_id}, ticker={ticker_symbol}, qty={quantity}")
                return transaction
        except SQLAlchemyError as exc:
            logger.error(f"Buy transaction failed and was rolled back: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def sell_stock(
        self, user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None
    ) -> Transaction:
        """Record a SELL transaction and decrease the matching portfolio holding atomically."""
        validate_positive_number(quantity, "quantity")
        validate_positive_number(price_per_unit, "price_per_unit")
        ticker_symbol = ticker_symbol.strip().upper()
        total_amount = quantity * price_per_unit

        try:
            with db_connection.get_session() as session:
                existing_holding = crud.get_one_by(session, Portfolio, user_id=user_id, ticker_symbol=ticker_symbol)
                if existing_holding is None or float(existing_holding.quantity) < quantity:
                    held_qty = float(existing_holding.quantity) if existing_holding else 0.0
                    raise ValidationError(
                        f"Cannot sell {quantity} shares of {ticker_symbol}; only {held_qty} are held."
                    )

                transaction = crud.create(
                    session,
                    Transaction(
                        user_id=user_id,
                        ticker_symbol=ticker_symbol,
                        transaction_type=TransactionType.SELL.value,
                        quantity=quantity,
                        price_per_unit=price_per_unit,
                        total_amount=total_amount,
                        transaction_date=datetime.utcnow(),
                        notes=notes,
                    ),
                )

                remaining_quantity = float(existing_holding.quantity) - quantity
                if remaining_quantity == 0:
                    crud.delete_by_id(session, Portfolio, existing_holding.portfolio_id, "portfolio_id")
                else:
                    crud.update_by_id(
                        session,
                        Portfolio,
                        existing_holding.portfolio_id,
                        "portfolio_id",
                        {"quantity": remaining_quantity},
                    )

                session.expunge(transaction)
                logger.info(f"SELL recorded: user_id={user_id}, ticker={ticker_symbol}, qty={quantity}")
                return transaction
        except ValidationError:
            raise
        except SQLAlchemyError as exc:
            logger.error(f"Sell transaction failed and was rolled back: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Read / History / Search
    # ------------------------------------------------------
    def transaction_history(
        self, user_id: int, page: int = 1, page_size: int = 25, ticker_symbol: str | None = None
    ) -> dict[str, Any]:
        """List a user's transactions, newest first, optionally filtered by ticker."""
        filters: dict[str, Any] = {"user_id": user_id}
        if ticker_symbol:
            filters["ticker_symbol"] = ticker_symbol.strip().upper()
        return self.list(
            filters=filters, sort_by="transaction_date", sort_direction="desc", page=page, page_size=page_size
        )

    def search_transactions(
        self, user_id: int, search_term: str, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        """Search a user's transactions by ticker symbol or notes."""
        return self.list(
            filters={"user_id": user_id},
            search_term=search_term,
            search_columns=["ticker_symbol", "notes"],
            sort_by="transaction_date",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )


transaction_service = TransactionService()
