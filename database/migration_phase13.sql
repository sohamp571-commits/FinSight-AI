-- ==========================================================
-- FinSight AI - Phase 13 Migration
-- Virtual Trading / Paper Trading module.
--
-- Run this ONLY if your database was already initialized before
-- Phase 13. It adds the virtual_accounts, virtual_holdings, and
-- virtual_transactions tables in place, without dropping or
-- altering any existing table (users, portfolio, transactions, or
-- any other Phase 1-12 table are left completely untouched).
--
-- If you have NOT initialized the database yet, just run the updated
-- database/schema.sql (or database/init_db.py) instead -- both
-- already include these tables.
--
-- Design notes:
--   - Virtual trading data is intentionally kept in its own tables
--     (virtual_accounts / virtual_holdings / virtual_transactions)
--     rather than reusing `portfolio` / `transactions` with an
--     `is_virtual` flag, so that real-money and paper-trading data
--     can never accidentally mix in a query that forgets a filter.
--   - Table shapes deliberately mirror `portfolio` and `transactions`
--     (same column names/types/constraints/index style) so the
--     existing service-layer patterns (BaseService, crud.py,
--     weighted-average cost basis, realized P&L replay) can be
--     reused with minimal adaptation in a later phase.
--   - Every table carries user_id with ON DELETE CASCADE, matching
--     the existing user-isolation pattern used by every other
--     per-user table in this schema.
-- ==========================================================

USE finsight_ai;

-- ==========================================================
-- virtual_accounts
-- --------------------------------------------------------
-- One row per user: tracks virtual cash balance and the account's
-- starting capital, independent of the user's real portfolio. Kept
-- as its own table (rather than a `settings` column) because it
-- needs its own audit trail and a `reset_at` timestamp for the
-- "safe reset virtual account" feature.
-- ==========================================================
CREATE TABLE IF NOT EXISTS virtual_accounts (
    virtual_account_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id              BIGINT        NOT NULL,
    initial_capital       DECIMAL(18,4) NOT NULL DEFAULT 1000000.0000,
    cash_balance            DECIMAL(18,4) NOT NULL DEFAULT 1000000.0000,
    created_at                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                 DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    reset_at                    DATETIME      NULL,
    CONSTRAINT uq_virtual_accounts_user UNIQUE (user_id),
    CONSTRAINT fk_virtual_accounts_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ==========================================================
-- virtual_holdings
-- --------------------------------------------------------
-- Mirrors the `portfolio` table's shape exactly (user_id,
-- ticker_symbol, quantity, average_buy_price, timestamps), but holds
-- paper-trading positions instead of real ones.
-- ==========================================================
CREATE TABLE IF NOT EXISTS virtual_holdings (
    virtual_holding_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id              BIGINT        NOT NULL,
    ticker_symbol         VARCHAR(20)   NOT NULL,
    quantity               DECIMAL(18,4) NOT NULL DEFAULT 0,
    average_buy_price       DECIMAL(18,4) NOT NULL DEFAULT 0,
    created_at                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                 DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_virtual_holdings_user_ticker UNIQUE (user_id, ticker_symbol),
    CONSTRAINT fk_virtual_holdings_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_virtual_holdings_ticker (ticker_symbol)
) ENGINE=InnoDB;

-- ==========================================================
-- virtual_transactions
-- --------------------------------------------------------
-- Mirrors the `transactions` table's shape exactly (the permanent,
-- append-only BUY/SELL ledger), but for paper trades. Kept separate
-- from `transactions` so realized P&L replay, audit history, and
-- reset all operate on an isolated ledger that never touches real
-- trading history.
-- ==========================================================
CREATE TABLE IF NOT EXISTS virtual_transactions (
    virtual_transaction_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id                  BIGINT        NOT NULL,
    ticker_symbol             VARCHAR(20)   NOT NULL,
    transaction_type           ENUM('BUY','SELL') NOT NULL,
    quantity                     DECIMAL(18,4) NOT NULL,
    price_per_unit                 DECIMAL(18,4) NOT NULL,
    total_amount                     DECIMAL(18,4) NOT NULL,
    cash_balance_after                 DECIMAL(18,4) NOT NULL,
    transaction_date                     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                                  VARCHAR(255)  NULL,
    CONSTRAINT fk_virtual_transactions_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_virtual_transactions_ticker (ticker_symbol),
    INDEX idx_virtual_transactions_user_date (user_id, transaction_date)
) ENGINE=InnoDB;
