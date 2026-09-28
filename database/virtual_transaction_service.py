"""
database/virtual_transaction_service.py

Purpose: Data-layer service for the `virtual_transactions` table --
the permanent, append-only paper-trading BUY/SELL ledger. Buying or
selling virtually must also debit/credit `virtual_accounts.cash_balance`
and update the matching `virtual_holdings` row. To guarantee all three
writes succeed or fail together, `buy_stock`/`sell_stock` use a single
explicit session (via crud.py) rather than delegating to
VirtualAccountService/VirtualHoldingService (each of which would open
its own, independent transaction) -- exactly the same reasoning
documented at the top of `database/transaction_service.py` for the
real (non-virtual) buy/sell flow, with one addition: virtual trading
also has a cash balance that must be validated and mutated atomically,
which the real portfolio has no equivalent of.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from constants import VIRTUAL_TRADING_INITIAL_CAPITAL, TransactionType
from custom_exceptions import DatabaseQueryError, RecordNotFoundError, ValidationError
from database import crud
from database.base_service import BaseService
from database.connection import db_connection
from database.models import User, VirtualAccount, VirtualHolding, VirtualTransaction
from logging_config import logger
from utils import is_valid_ticker, safe_divide, validate_positive_number


class VirtualTransactionService(BaseService[VirtualTransaction]):
    """CRUD and buy/sell operations for the `virtual_transactions` table."""

    model = VirtualTransaction
    pk_column = "virtual_transaction_id"

    # ------------------------------------------------------
    # Buy / Sell (atomic with virtual_accounts + virtual_holdings)
    # ------------------------------------------------------
    def buy_stock(
        self, user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None
    ) -> VirtualTransaction:
        """
        Record a virtual BUY transaction, debit virtual cash, and
        increase the matching virtual holding -- all atomically. If
        the user has no virtual account yet, one is created and seeded
        with the default starting capital in the same transaction.

        Raises:
            ValidationError: invalid quantity/price/ticker, or insufficient virtual cash.
            RecordNotFoundError: `user_id` does not correspond to an existing user.
            DatabaseQueryError: any other database failure (transaction is rolled back).
        """
        validate_positive_number(quantity, "quantity")
        validate_positive_number(price_per_unit, "price_per_unit")
        ticker_symbol = ticker_symbol.strip().upper()
        if not is_valid_ticker(ticker_symbol):
            raise ValidationError(f"'{ticker_symbol}' is not a valid ticker symbol.")
        total_amount = quantity * price_per_unit

        try:
            with db_connection.get_session() as session:
                if crud.get_by_id(session, User, user_id, "user_id") is None:
                    raise RecordNotFoundError(f"No user found with user_id={user_id}.")

                account = crud.get_one_by(session, VirtualAccount, user_id=user_id)
                if account is None:
                    account = crud.create(
                        session,
                        VirtualAccount(
                            user_id=user_id,
                            initial_capital=VIRTUAL_TRADING_INITIAL_CAPITAL,
                            cash_balance=VIRTUAL_TRADING_INITIAL_CAPITAL,
                        ),
                    )

                current_cash = float(account.cash_balance)
                if current_cash < total_amount:
                    raise ValidationError(
                        f"Insufficient virtual cash: balance is ₹{current_cash:,.2f}, "
                        f"order requires ₹{total_amount:,.2f}."
                    )
                new_cash_balance = current_cash - total_amount

                transaction = crud.create(
                    session,
                    VirtualTransaction(
                        user_id=user_id,
                        ticker_symbol=ticker_symbol,
                        transaction_type=TransactionType.BUY.value,
                        quantity=quantity,
                        price_per_unit=price_per_unit,
                        total_amount=total_amount,
                        cash_balance_after=new_cash_balance,
                        transaction_date=datetime.utcnow(),
                        notes=notes,
                    ),
                )

                existing_holding = crud.get_one_by(
                    session, VirtualHolding, user_id=user_id, ticker_symbol=ticker_symbol
                )
                if existing_holding is None:
                    crud.create(
                        session,
                        VirtualHolding(
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
                        VirtualHolding,
                        existing_holding.virtual_holding_id,
                        "virtual_holding_id",
                        {"quantity": combined_quantity, "average_buy_price": new_average_price},
                    )

                crud.update_by_id(
                    session, VirtualAccount, account.virtual_account_id, "virtual_account_id",
                    {"cash_balance": new_cash_balance},
                )

                session.expunge(transaction)
                logger.info(
                    f"Virtual BUY recorded: user_id={user_id}, ticker={ticker_symbol}, "
                    f"qty={quantity}, cash_balance_after={new_cash_balance}"
                )
                return transaction
        except (ValidationError, RecordNotFoundError):
            raise
        except SQLAlchemyError as exc:
            logger.error(f"Virtual buy transaction failed and was rolled back: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def sell_stock(
        self, user_id: int, ticker_symbol: str, quantity: float, price_per_unit: float, notes: str | None = None
    ) -> VirtualTransaction:
        """
        Record a virtual SELL transaction, credit virtual cash, and
        decrease (or fully remove) the matching virtual holding -- all
        atomically.

        Raises:
            ValidationError: invalid quantity/price/ticker, or insufficient virtual holdings.
            RecordNotFoundError: `user_id` does not correspond to an existing user.
            DatabaseQueryError: any other database failure (transaction is rolled back).
        """
        validate_positive_number(quantity, "quantity")
        validate_positive_number(price_per_unit, "price_per_unit")
        ticker_symbol = ticker_symbol.strip().upper()
        if not is_valid_ticker(ticker_symbol):
            raise ValidationError(f"'{ticker_symbol}' is not a valid ticker symbol.")
        total_amount = quantity * price_per_unit

        try:
            with db_connection.get_session() as session:
                if crud.get_by_id(session, User, user_id, "user_id") is None:
                    raise RecordNotFoundError(f"No user found with user_id={user_id}.")

                existing_holding = crud.get_one_by(
                    session, VirtualHolding, user_id=user_id, ticker_symbol=ticker_symbol
                )
                if existing_holding is None or float(existing_holding.quantity) < quantity:
                    held_qty = float(existing_holding.quantity) if existing_holding else 0.0
                    raise ValidationError(
                        f"Cannot sell {quantity} shares of {ticker_symbol}; "
                        f"only {held_qty} are held in your virtual account."
                    )

                account = crud.get_one_by(session, VirtualAccount, user_id=user_id)
                if account is None:
                    # A holding exists but no account row -- should not happen in
                    # practice (buy_stock always creates the account first), but
                    # guard against it rather than crash on a None dereference.
                    raise RecordNotFoundError("No virtual trading account exists for this user.")

                new_cash_balance = float(account.cash_balance) + total_amount

                transaction = crud.create(
                    session,
                    VirtualTransaction(
                        user_id=user_id,
                        ticker_symbol=ticker_symbol,
                        transaction_type=TransactionType.SELL.value,
                        quantity=quantity,
                        price_per_unit=price_per_unit,
                        total_amount=total_amount,
                        cash_balance_after=new_cash_balance,
                        transaction_date=datetime.utcnow(),
                        notes=notes,
                    ),
                )

                remaining_quantity = float(existing_holding.quantity) - quantity
                if remaining_quantity == 0:
                    crud.delete_by_id(session, VirtualHolding, existing_holding.virtual_holding_id, "virtual_holding_id")
                else:
                    crud.update_by_id(
                        session,
                        VirtualHolding,
                        existing_holding.virtual_holding_id,
                        "virtual_holding_id",
                        {"quantity": remaining_quantity},
                    )

                crud.update_by_id(
                    session, VirtualAccount, account.virtual_account_id, "virtual_account_id",
                    {"cash_balance": new_cash_balance},
                )

                session.expunge(transaction)
                logger.info(
                    f"Virtual SELL recorded: user_id={user_id}, ticker={ticker_symbol}, "
                    f"qty={quantity}, cash_balance_after={new_cash_balance}"
                )
                return transaction
        except (ValidationError, RecordNotFoundError):
            raise
        except SQLAlchemyError as exc:
            logger.error(f"Virtual sell transaction failed and was rolled back: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Read / History / Search
    # ------------------------------------------------------
    def transaction_history(
        self, user_id: int, page: int = 1, page_size: int = 25, ticker_symbol: str | None = None
    ) -> dict[str, Any]:
        """List a user's virtual transactions, newest first, optionally filtered by ticker."""
        filters: dict[str, Any] = {"user_id": user_id}
        if ticker_symbol:
            filters["ticker_symbol"] = ticker_symbol.strip().upper()
        return self.list(
            filters=filters, sort_by="transaction_date", sort_direction="desc", page=page, page_size=page_size
        )

    def search_transactions(
        self, user_id: int, search_term: str, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        """Search a user's virtual transactions by ticker symbol or notes."""
        return self.list(
            filters={"user_id": user_id},
            search_term=search_term,
            search_columns=["ticker_symbol", "notes"],
            sort_by="transaction_date",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )


virtual_transaction_service = VirtualTransactionService()
