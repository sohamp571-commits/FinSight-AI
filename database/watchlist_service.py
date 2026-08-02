"""
database/watchlist_service.py

Purpose: Data-layer service for the `watchlist` table. Deliberately
small/simple -- watchlist entries have no computed state (unlike
portfolio holdings), so this is close to a pure CRUD wrapper with a
uniqueness guard.
"""

from typing import Any

from constants import MAX_WATCHLIST_ITEMS
from custom_exceptions import DuplicateRecordError, ValidationError
from database.base_service import BaseService
from database.models import Watchlist
from logging_config import logger
from utils import is_valid_ticker


class WatchlistService(BaseService[Watchlist]):
    """CRUD operations for the `watchlist` table."""

    model = Watchlist
    pk_column = "watchlist_id"

    def add_stock(self, user_id: int, ticker_symbol: str) -> Watchlist:
        """Add a ticker to a user's watchlist, enforcing per-user uniqueness and a size cap."""
        ticker_symbol = ticker_symbol.strip().upper()
        if not is_valid_ticker(ticker_symbol):
            raise ValidationError(f"'{ticker_symbol}' is not a valid ticker symbol.")

        if self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol) is not None:
            raise DuplicateRecordError(f"{ticker_symbol} is already in your watchlist.")

        current_count = self.count(filters={"user_id": user_id})
        if current_count >= MAX_WATCHLIST_ITEMS:
            raise ValidationError(f"Watchlist is limited to {MAX_WATCHLIST_ITEMS} tickers.")

        entry = self.create(Watchlist(user_id=user_id, ticker_symbol=ticker_symbol))
        logger.info(f"Watchlist: added {ticker_symbol} for user_id={user_id}")
        return entry

    def remove_stock(self, user_id: int, ticker_symbol: str) -> None:
        """Remove a ticker from a user's watchlist."""
        ticker_symbol = ticker_symbol.strip().upper()
        entry = self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol)
        if entry is None:
            raise ValidationError(f"{ticker_symbol} is not in your watchlist.")
        self.delete(entry.watchlist_id)
        logger.info(f"Watchlist: removed {ticker_symbol} for user_id={user_id}")

    def list_watchlist(self, user_id: int, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """List every ticker in a user's watchlist, most recently added first."""
        return self.list(
            filters={"user_id": user_id}, sort_by="added_at", sort_direction="desc", page=page, page_size=page_size
        )

    def is_watching(self, user_id: int, ticker_symbol: str) -> bool:
        """Return True if the user is already watching the given ticker."""
        return self.find_one_by(user_id=user_id, ticker_symbol=ticker_symbol.strip().upper()) is not None


watchlist_service = WatchlistService()
