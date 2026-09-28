"""
database/virtual_account_service.py

Purpose: Data-layer service for the `virtual_accounts` table -- one
virtual cash account per user for the Virtual Trading / Paper Trading
module (Phase 13). Deliberately mirrors the shape of
`database/watchlist_service.py` (a small CRUD service with a
uniqueness guard), since `virtual_accounts` has one row per user
enforced by a DB-level UNIQUE(user_id) constraint.

Note: The cash-balance mutations here (`credit_cash`/`debit_cash`)
are standalone, single-table operations (e.g. for account reset or
manual adjustment). They are intentionally NOT used by the atomic
buy/sell flow in `virtual_transaction_service.py`, which must update
`virtual_accounts` and `virtual_holdings` and `virtual_transactions`
together in a single session -- exactly the same reasoning documented
at the top of `database/transaction_service.py`.
"""

from datetime import datetime
from typing import Any

from constants import VIRTUAL_TRADING_INITIAL_CAPITAL
from custom_exceptions import DuplicateRecordError, RecordNotFoundError, ValidationError
from database.base_service import BaseService
from database.models import VirtualAccount
from logging_config import logger
from utils import validate_positive_number


class VirtualAccountService(BaseService[VirtualAccount]):
    """CRUD and cash-balance operations for the `virtual_accounts` table."""

    model = VirtualAccount
    pk_column = "virtual_account_id"

    # ------------------------------------------------------
    # Get / Create
    # ------------------------------------------------------
    def get_or_create(self, user_id: int) -> VirtualAccount:
        """
        Fetch a user's virtual account, creating one seeded with the
        default virtual capital if it doesn't exist yet. Safe to call
        repeatedly -- the DB-level UNIQUE(user_id) constraint is the
        final guard against a user ever ending up with two accounts
        (e.g. two concurrent first-time page loads race each other).
        """
        existing = self.find_one_by(user_id=user_id)
        if existing is not None:
            return existing

        try:
            account = self.create(
                VirtualAccount(
                    user_id=user_id,
                    initial_capital=VIRTUAL_TRADING_INITIAL_CAPITAL,
                    cash_balance=VIRTUAL_TRADING_INITIAL_CAPITAL,
                )
            )
            logger.info(f"Virtual account created: user_id={user_id}, initial_capital={VIRTUAL_TRADING_INITIAL_CAPITAL}")
            return account
        except DuplicateRecordError:
            # Lost a create-race to a concurrent request; the account
            # now exists, so fetch and return it instead of failing.
            existing = self.find_one_by(user_id=user_id)
            if existing is None:
                raise
            return existing

    def get_account(self, user_id: int) -> VirtualAccount:
        """Fetch a user's virtual account, raising if it hasn't been created yet."""
        account = self.find_one_by(user_id=user_id)
        if account is None:
            raise RecordNotFoundError("No virtual trading account exists for this user yet.")
        return account

    # ------------------------------------------------------
    # Read
    # ------------------------------------------------------
    def get_cash_balance(self, user_id: int) -> float:
        """Return a user's current virtual cash balance (creates the account if missing)."""
        return float(self.get_or_create(user_id).cash_balance)

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def credit_cash(self, user_id: int, amount: float) -> VirtualAccount:
        """Increase a user's virtual cash balance by `amount` (e.g. a standalone/manual adjustment)."""
        validate_positive_number(amount, "amount")
        account = self.get_or_create(user_id)
        new_balance = float(account.cash_balance) + amount
        updated = self.update(account.virtual_account_id, {"cash_balance": new_balance})
        logger.info(f"Virtual cash credited: user_id={user_id}, amount={amount}, new_balance={new_balance}")
        return updated

    def debit_cash(self, user_id: int, amount: float) -> VirtualAccount:
        """Decrease a user's virtual cash balance by `amount`, rejecting if funds are insufficient."""
        validate_positive_number(amount, "amount")
        account = self.get_or_create(user_id)
        current_balance = float(account.cash_balance)
        if current_balance < amount:
            raise ValidationError(
                f"Insufficient virtual cash: balance is ₹{current_balance:,.2f}, requested ₹{amount:,.2f}."
            )
        new_balance = current_balance - amount
        updated = self.update(account.virtual_account_id, {"cash_balance": new_balance})
        logger.info(f"Virtual cash debited: user_id={user_id}, amount={amount}, new_balance={new_balance}")
        return updated

    def reset_account(self, user_id: int) -> VirtualAccount:
        """
        Reset a user's virtual account cash balance back to its
        original starting capital and stamp `reset_at`. Does NOT touch
        `virtual_holdings` or `virtual_transactions` -- clearing those
        is the responsibility of the reset workflow built in a later
        batch, which should call this alongside deleting those rows so
        the whole reset stays consistent with a fresh cash balance.
        """
        account = self.get_or_create(user_id)
        updated = self.update(
            account.virtual_account_id,
            {"cash_balance": float(account.initial_capital), "reset_at": datetime.utcnow()},
        )
        logger.info(f"Virtual account reset: user_id={user_id}, cash_balance={updated.cash_balance}")
        return updated

    # ------------------------------------------------------
    # Reporting
    # ------------------------------------------------------
    def account_summary(self, user_id: int) -> dict[str, Any]:
        """Return a small summary dict of a user's virtual account (cash, capital, timestamps)."""
        account = self.get_or_create(user_id)
        return {
            "virtual_account_id": account.virtual_account_id,
            "initial_capital": float(account.initial_capital),
            "cash_balance": float(account.cash_balance),
            "created_at": account.created_at,
            "updated_at": account.updated_at,
            "reset_at": account.reset_at,
        }


virtual_account_service = VirtualAccountService()
