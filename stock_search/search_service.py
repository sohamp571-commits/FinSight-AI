"""
stock_search/search_service.py

Purpose: The business-logic layer for the Stock Search module --
Streamlit-free, mirroring `authentication/auth_service.py`'s role in
that package. Handles:
    - Resolving free-text input (company name, NSE symbol, BSE symbol)
      to a validated yfinance ticker
    - Auto-complete suggestions against a static company directory
    - Recording/reading a user's search history (new `search_history`
      table) directly via `database.base_service.BaseService`, the
      same pattern `authentication/auth_service.py` uses for `User`
    - "Favorite companies" by delegating to the existing
      `database.watchlist_service` (a favorite IS a watched ticker)
"""

from datetime import datetime
from difflib import SequenceMatcher

from custom_exceptions import ValidationError
from dashboard.market_data_service import NIFTY50_UNIVERSE, fetch_quote
from database.base_service import BaseService
from database.models import SearchHistory
from database.watchlist_service import watchlist_service
from logging_config import logger
from utils import is_valid_ticker

# A broader static directory than the dashboard's 30-ticker universe,
# used for name/symbol autocomplete. Extends NIFTY50_UNIVERSE with a
# few additional well-known large caps and global tickers so search
# isn't limited to exactly the dashboard's heatmap set.
COMPANY_DIRECTORY: dict[str, str] = {
    **NIFTY50_UNIVERSE,
    "APOLLOHOSP.NS": "Apollo Hospitals",
    "DIVISLAB.NS": "Divi's Laboratories",
    "BRITANNIA.NS": "Britannia Industries",
    "CIPLA.NS": "Cipla",
    "DRREDDY.NS": "Dr. Reddy's Laboratories",
    "EICHERMOT.NS": "Eicher Motors",
    "GRASIM.NS": "Grasim Industries",
    "HEROMOTOCO.NS": "Hero MotoCorp",
    "HINDALCO.NS": "Hindalco Industries",
    "INDUSINDBK.NS": "IndusInd Bank",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "NVDA": "NVIDIA Corporation",
}

_HISTORY_LIMIT = 15


class SearchHistoryService(BaseService[SearchHistory]):
    """CRUD for the `search_history` table, following the same BaseService pattern as database/*_service.py."""

    model = SearchHistory
    pk_column = "search_id"


search_history_service = SearchHistoryService()


# ==========================================================
# Ticker Resolution / Validation
# ==========================================================
def resolve_ticker(raw_query: str) -> str:
    """
    Resolve free-text user input into a yfinance-compatible ticker.

    Resolution order:
        1. Exact match against the company directory's ticker keys (NSE/BSE symbol as typed)
        2. Exact (case-insensitive) match against the company directory's names
        3. Fuzzy best-match against directory names (for typos / partial names)
        4. As-typed, uppercased, assumed already a valid global ticker (e.g. "AAPL")

    Raises:
        ValidationError: if `raw_query` is empty.
    """
    query = raw_query.strip()
    if not query:
        raise ValidationError("Please enter a company name or ticker symbol to search.")

    upper_query = query.upper()

    # 1. Exact ticker match (as typed, or with .NS/.BO appended)
    for candidate in (upper_query, f"{upper_query}.NS", f"{upper_query}.BO"):
        if candidate in COMPANY_DIRECTORY:
            return candidate

    # 2. Exact company-name match (case-insensitive)
    for ticker, name in COMPANY_DIRECTORY.items():
        if name.lower() == query.lower():
            return ticker

    # 3. Fuzzy name match
    best_ticker, best_score = None, 0.0
    for ticker, name in COMPANY_DIRECTORY.items():
        score = SequenceMatcher(None, query.lower(), name.lower()).ratio()
        if score > best_score:
            best_ticker, best_score = ticker, score
    if best_score >= 0.6:
        return best_ticker

    # 4. Fall back to the raw, uppercased query -- validated by the caller via validate_ticker_exists()
    return upper_query


def validate_ticker_exists(ticker: str) -> bool:
    """
    Confirm a ticker actually resolves to real yfinance data (handles
    the "invalid ticker" requirement gracefully instead of crashing
    downstream pages). Reuses market_data_service.fetch_quote, which
    already applies caching and retry logic.
    """
    quote = fetch_quote(ticker)
    if quote is None:
        logger.warning(f"Ticker validation failed for '{ticker}'.")
        return False
    return True


def get_autocomplete_suggestions(partial_query: str, limit: int = 8) -> list[dict[str, str]]:
    """
    Return up to `limit` autocomplete suggestions matching a partial
    company name or ticker symbol, ranked by match quality.

    Returns:
        [{"ticker": str, "name": str}, ...]
    """
    partial = partial_query.strip().lower()
    if not partial:
        return []

    scored: list[tuple[float, dict[str, str]]] = []
    for ticker, name in COMPANY_DIRECTORY.items():
        ticker_bare = ticker.replace(".NS", "").replace(".BO", "").lower()
        name_lower = name.lower()

        if partial in ticker_bare or partial in name_lower:
            # Prefix matches rank highest, substring matches next.
            score = 1.0 if name_lower.startswith(partial) or ticker_bare.startswith(partial) else 0.7
            scored.append((score, {"ticker": ticker, "name": name}))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


# ==========================================================
# Search History
# ==========================================================
def log_search(user_id: int, search_query: str, ticker_symbol: str | None) -> None:
    """
    Record a search in `search_history`. Best-effort: a logging
    failure must never block the user from seeing their search
    results, mirroring `audit_service.log_action`'s philosophy.
    """
    try:
        search_history_service.create(
            SearchHistory(
                user_id=user_id,
                search_query=search_query.strip(),
                ticker_symbol=ticker_symbol,
                searched_at=datetime.utcnow(),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to log search history for user_id={user_id}: {exc}")


def get_recent_searches(user_id: int, limit: int = _HISTORY_LIMIT) -> list[SearchHistory]:
    """Return a user's most recent searches, newest first, de-duplicated by ticker."""
    result = search_history_service.list(
        filters={"user_id": user_id}, sort_by="searched_at", sort_direction="desc", page_size=limit * 2
    )
    seen_tickers: set[str] = set()
    deduped: list[SearchHistory] = []
    for entry in result["items"]:
        key = entry.ticker_symbol or entry.search_query
        if key in seen_tickers:
            continue
        seen_tickers.add(key)
        deduped.append(entry)
        if len(deduped) >= limit:
            break
    return deduped


def clear_search_history(user_id: int) -> int:
    """Delete every search_history row for a user. Returns the number of rows removed."""
    result = search_history_service.list(filters={"user_id": user_id}, page_size=1000)
    for entry in result["items"]:
        search_history_service.delete(entry.search_id)
    logger.info(f"Cleared {len(result['items'])} search history entries for user_id={user_id}")
    return len(result["items"])


# ==========================================================
# Favorites (delegates to the existing watchlist_service)
# ==========================================================
def is_favorite(user_id: int, ticker: str) -> bool:
    """A company is a "favorite" if it's on the user's watchlist."""
    return watchlist_service.is_watching(user_id, ticker)


def toggle_favorite(user_id: int, ticker: str) -> bool:
    """
    Add or remove a ticker from favorites (the watchlist table).

    Returns:
        True if the ticker is now favorited, False if it was just removed.
    """
    if is_favorite(user_id, ticker):
        watchlist_service.remove_stock(user_id, ticker)
        return False
    if not is_valid_ticker(ticker.replace(".NS", "").replace(".BO", "")):
        raise ValidationError(f"'{ticker}' is not a valid ticker symbol.")
    watchlist_service.add_stock(user_id, ticker)
    return True
