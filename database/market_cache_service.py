"""
database/market_cache_service.py

Purpose: Data-layer service for the `market_cache` table -- stores
daily OHLCV (open/high/low/close/volume) bars fetched from yfinance,
so repeated chart/analytics requests don't repeatedly hit the external
API for the same historical day. Upserts on (ticker_symbol, data_date)
per the table's unique constraint.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from custom_exceptions import DatabaseQueryError, ValidationError
from database import crud
from database.base_service import BaseService
from database.connection import db_connection
from database.models import MarketCache
from logging_config import logger
from utils import validate_positive_number


class MarketCacheService(BaseService[MarketCache]):
    """CRUD and upsert operations for the `market_cache` table."""

    model = MarketCache
    pk_column = "market_cache_id"

    def upsert_bar(
        self,
        ticker_symbol: str,
        data_date: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
    ) -> MarketCache:
        """Insert a new daily bar, or update it in place if one already exists for that date."""
        for label, value in (
            ("open_price", open_price),
            ("high_price", high_price),
            ("low_price", low_price),
            ("close_price", close_price),
        ):
            validate_positive_number(value, label)
        if volume < 0:
            raise ValidationError("volume cannot be negative.")

        ticker_symbol = ticker_symbol.strip().upper()
        try:
            with db_connection.get_session() as session:
                existing = crud.get_one_by(session, MarketCache, ticker_symbol=ticker_symbol, data_date=data_date)
                payload = {
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "close_price": close_price,
                    "volume": volume,
                }
                if existing is None:
                    bar = crud.create(
                        session,
                        MarketCache(ticker_symbol=ticker_symbol, data_date=data_date, **payload),
                    )
                else:
                    bar = crud.update_by_id(
                        session, MarketCache, existing.market_cache_id, "market_cache_id", payload
                    )
                session.expunge(bar)
                return bar
        except SQLAlchemyError as exc:
            logger.error(f"Failed to upsert market_cache bar: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def bulk_upsert_bars(self, ticker_symbol: str, bars: list[dict[str, Any]]) -> int:
        """
        Upsert many daily bars for a ticker in one pass (e.g. a full
        yfinance history download). Returns the number of bars processed.
        """
        count = 0
        for bar in bars:
            self.upsert_bar(
                ticker_symbol=ticker_symbol,
                data_date=bar["data_date"],
                open_price=bar["open_price"],
                high_price=bar["high_price"],
                low_price=bar["low_price"],
                close_price=bar["close_price"],
                volume=bar["volume"],
            )
            count += 1
        logger.info(f"Bulk-upserted {count} market_cache bar(s) for {ticker_symbol}.")
        return count

    def get_price_history(self, ticker_symbol: str, page: int = 1, page_size: int = 100) -> dict[str, Any]:
        """Fetch cached OHLCV history for a ticker, most recent date first."""
        return self.list(
            filters={"ticker_symbol": ticker_symbol.strip().upper()},
            sort_by="data_date",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )


market_cache_service = MarketCacheService()
