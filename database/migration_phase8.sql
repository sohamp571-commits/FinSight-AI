-- ==========================================================
-- FinSight AI - Phase 8 Migration
-- Run this ONLY if your database was already initialized before
-- Phase 8. It adds the ipo_listings, notifications, and
-- notification_preferences tables in place, without dropping or
-- recreating any existing table.
--
-- If you have NOT initialized the database yet, just run the updated
-- database/schema.sql (or database/init_db.py) instead -- both
-- already include these tables.
-- ==========================================================

USE finsight_ai;

CREATE TABLE IF NOT EXISTS ipo_listings (
    ipo_id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    company_name         VARCHAR(150)  NOT NULL,
    ticker_symbol        VARCHAR(20)   NULL,
    exchange             VARCHAR(20)   NOT NULL DEFAULT 'NSE',
    issue_price_min      DECIMAL(10,2) NULL,
    issue_price_max      DECIMAL(10,2) NULL,
    lot_size             INT           NULL,
    open_date            DATETIME      NULL,
    close_date           DATETIME      NULL,
    listing_date         DATETIME      NULL,
    status               ENUM('UPCOMING','OPEN','CLOSED','LISTED') NOT NULL DEFAULT 'UPCOMING',
    subscription_times   DECIMAL(8,2)  NULL,
    gmp                  DECIMAL(10,2) NULL,
    created_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ipo_status (status),
    INDEX idx_ipo_dates (open_date, close_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
    notification_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id            BIGINT        NOT NULL,
    notification_type  VARCHAR(50)   NOT NULL,
    title               VARCHAR(200)  NOT NULL,
    message              VARCHAR(1000) NOT NULL,
    priority              ENUM('LOW','MEDIUM','HIGH') NOT NULL DEFAULT 'MEDIUM',
    related_ticker         VARCHAR(20)   NULL,
    is_read                 TINYINT(1)    NOT NULL DEFAULT 0,
    is_archived              TINYINT(1)    NOT NULL DEFAULT 0,
    created_at                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_notifications_user_read (user_id, is_read, is_archived),
    INDEX idx_notifications_user_date (user_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notification_preferences (
    preference_id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id                    BIGINT      NOT NULL,
    ipo_open                    TINYINT(1)  NOT NULL DEFAULT 1,
    ipo_close                    TINYINT(1)  NOT NULL DEFAULT 1,
    ipo_listing                   TINYINT(1)  NOT NULL DEFAULT 1,
    watchlist_news                 TINYINT(1)  NOT NULL DEFAULT 1,
    watchlist_price_alerts          TINYINT(1)  NOT NULL DEFAULT 1,
    prediction_changes                TINYINT(1)  NOT NULL DEFAULT 0,
    market_opening                     TINYINT(1)  NOT NULL DEFAULT 0,
    market_closing                      TINYINT(1)  NOT NULL DEFAULT 0,
    portfolio_profit_target              TINYINT(1)  NOT NULL DEFAULT 1,
    portfolio_stop_loss                   TINYINT(1)  NOT NULL DEFAULT 1,
    market_crash_rally                     TINYINT(1)  NOT NULL DEFAULT 1,
    email_daily_digest                      TINYINT(1)  NOT NULL DEFAULT 0,
    email_weekly_digest                      TINYINT(1)  NOT NULL DEFAULT 0,
    email_instant_alerts                      TINYINT(1)  NOT NULL DEFAULT 1,
    updated_at                                 DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_notification_prefs_user UNIQUE (user_id),
    CONSTRAINT fk_notification_prefs_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;
