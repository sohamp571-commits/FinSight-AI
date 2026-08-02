"""
database/models.py

SQLAlchemy ORM models mapping to the normalized MySQL schema defined in
database/schema.sql. These models are the single source of truth for
table structure from the Python side; database/init_db.py uses
Base.metadata.create_all() to materialize them.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DECIMAL,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the project."""
    pass


# ==========================================================
# roles
# ==========================================================
class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


# ==========================================================
# users
# ==========================================================
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Phase 2: soft delete
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    role: Mapped["Role"] = relationship(
        back_populates="users",
        lazy="joined"
    )
    portfolio_items: Mapped[list["Portfolio"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watchlist_items: Mapped[list["Watchlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    predictions: Mapped[list["PredictionHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    settings: Mapped["Settings"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)


# ==========================================================
# portfolio
# ==========================================================
class Portfolio(Base):
    __tablename__ = "portfolio"
    __table_args__ = (UniqueConstraint("user_id", "ticker_symbol", name="uq_portfolio_user_ticker"),)

    portfolio_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False, default=0)
    average_buy_price: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="portfolio_items")


# ==========================================================
# transactions
# ==========================================================
class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY / SELL
    quantity: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    price_per_unit: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    total_amount: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="transactions")


# ==========================================================
# watchlist
# ==========================================================
class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "ticker_symbol", name="uq_watchlist_user_ticker"),)

    watchlist_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="watchlist_items")


# ==========================================================
# prediction_history
# ==========================================================
class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    prediction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_price: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    prediction_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="predictions")


# ==========================================================
# reports
# ==========================================================
class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="reports")


# ==========================================================
# news_cache
# ==========================================================
class NewsCache(Base):
    __tablename__ = "news_cache"

    news_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sentiment_score: Mapped[float | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_news_ticker_published", "ticker_symbol", "published_at"),)


# ==========================================================
# market_cache
# ==========================================================
class MarketCache(Base):
    __tablename__ = "market_cache"
    __table_args__ = (UniqueConstraint("ticker_symbol", "data_date", name="uq_market_ticker_date"),)

    market_cache_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    data_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open_price: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    high_price: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    low_price: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    close_price: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ==========================================================
# alerts
# ==========================================================
class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    condition_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_value: Mapped[float] = mapped_column(DECIMAL(18, 4), nullable=False)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="alerts")


# ==========================================================
# audit_logs
# ==========================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="audit_logs")


# ==========================================================
# settings
# ==========================================================
class Settings(Base):
    __tablename__ = "settings"

    settings_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    theme: Mapped[str] = mapped_column(String(20), default="light", nullable=False)
    default_currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="settings")


# ==========================================================
# password_reset_tokens  (Phase 2 addition)
# --------------------------------------------------------
# Needed because "Forgot Password" / "Reset Password" requires a
# single-use, time-limited, revocable token that is NOT the user's
# session token and NOT stored in plaintext. None of the Phase 1
# tables can safely hold this.
# ==========================================================
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship()


# ==========================================================
# login_history  (Phase 2 addition)
# --------------------------------------------------------
# Needed to satisfy "Login History" / "Last Login" / brute-force
# lockout requirements. `users.last_login_at` only stores the most
# recent login; this table stores every attempt (success and failure)
# for auditing and MAX_LOGIN_ATTEMPTS enforcement.
# ==========================================================
class LoginHistory(Base):
    __tablename__ = "login_history"

    login_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    username_attempted: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # SUCCESS / FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship()


# ==========================================================
# search_history  (Phase 5 addition)
# --------------------------------------------------------
# Needed for "Recent Searches" / "Search History" / auto-complete
# ranking in the Stock Search module. No Phase 1-4 table stores
# free-text search queries or a per-user chronological search log.
# "Favorite Companies" intentionally reuses the existing `watchlist`
# table (user_id + ticker_symbol) rather than introducing a duplicate
# concept -- a favorited company IS a watched ticker in FinSight AI.
# ==========================================================
class SearchHistory(Base):
    __tablename__ = "search_history"

    search_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    search_query: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    searched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship()


# ==========================================================
# ipo_listings  (Phase 8 addition)
# --------------------------------------------------------
# Needed because no Phase 1-7 table stores IPO calendar data (issue
# price, subscription status, GMP, listing date). `market_cache` is
# for already-listed tickers' daily OHLCV, which doesn't fit an IPO
# that hasn't listed yet.
# ==========================================================
class IPOListing(Base):
    __tablename__ = "ipo_listings"

    ipo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    ticker_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    exchange: Mapped[str] = mapped_column(String(20), default="NSE", nullable=False)
    issue_price_min: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    issue_price_max: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    lot_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    listing_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="UPCOMING", nullable=False)  # UPCOMING/OPEN/CLOSED/LISTED
    subscription_times: Mapped[float | None] = mapped_column(DECIMAL(8, 2), nullable=True)
    gmp: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)  # Grey Market Premium
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# ==========================================================
# notifications  (Phase 8 addition)
# --------------------------------------------------------
# Needed for the in-app Notification Center (unread count, mark read,
# delete, archive, priority). `alerts` (Phase 1) and `audit_logs`
# (Phase 2) are single-purpose (price triggers / security audit trail
# respectively) and neither models a general, user-facing, readable/
# dismissible notification feed spanning IPOs, news, predictions, and
# portfolio events.
# ==========================================================
class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM", nullable=False)  # LOW/MEDIUM/HIGH
    related_ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship()


# ==========================================================
# notification_preferences  (Phase 8 addition)
# --------------------------------------------------------
# Needed for granular per-category subscription toggles (IPO opens,
# watchlist news, prediction changes, market crash/rally, etc.).
# `settings.notifications_enabled` (Phase 1) remains the single
# master on/off switch; this table is the detailed breakdown beneath it.
# ==========================================================
class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    preference_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    ipo_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ipo_close: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ipo_listing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    watchlist_news: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    watchlist_price_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prediction_changes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    market_opening: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    market_closing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    portfolio_profit_target: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    portfolio_stop_loss: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    market_crash_rally: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_daily_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_weekly_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_instant_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship()
