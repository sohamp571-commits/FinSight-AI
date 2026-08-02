-- ==========================================================
-- FinSight AI - MySQL 8.0 Schema
-- Phase 1: Foundation tables only.
-- Charset: utf8mb4 | Engine: InnoDB | Timestamps on every table.
-- ==========================================================

CREATE DATABASE IF NOT EXISTS finsight_ai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE finsight_ai;

-- ==========================================================
-- roles
-- ==========================================================
CREATE TABLE IF NOT EXISTS roles (
    role_id      INT AUTO_INCREMENT PRIMARY KEY,
    role_name    VARCHAR(50)  NOT NULL,
    description  VARCHAR(255) NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_roles_role_name UNIQUE (role_name)
) ENGINE=InnoDB;

-- ==========================================================
-- users
-- ==========================================================
CREATE TABLE IF NOT EXISTS users (
    user_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(100)  NOT NULL,
    email          VARCHAR(150)  NOT NULL,
    username       VARCHAR(50)   NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,
    role_id        INT           NOT NULL,
    is_active      TINYINT(1)    NOT NULL DEFAULT 1,
    deleted_at     DATETIME      NULL,
    last_login_at  DATETIME      NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE RESTRICT,
    INDEX idx_users_email (email),
    INDEX idx_users_username (username)
) ENGINE=InnoDB;

-- ==========================================================
-- portfolio
-- ==========================================================
CREATE TABLE IF NOT EXISTS portfolio (
    portfolio_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id            BIGINT        NOT NULL,
    ticker_symbol      VARCHAR(20)   NOT NULL,
    quantity           DECIMAL(18,4) NOT NULL DEFAULT 0,
    average_buy_price  DECIMAL(18,4) NOT NULL DEFAULT 0,
    created_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_portfolio_user_ticker UNIQUE (user_id, ticker_symbol),
    CONSTRAINT fk_portfolio_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_portfolio_ticker (ticker_symbol)
) ENGINE=InnoDB;

-- ==========================================================
-- transactions
-- ==========================================================
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id           BIGINT        NOT NULL,
    ticker_symbol     VARCHAR(20)   NOT NULL,
    transaction_type  ENUM('BUY','SELL') NOT NULL,
    quantity          DECIMAL(18,4) NOT NULL,
    price_per_unit    DECIMAL(18,4) NOT NULL,
    total_amount      DECIMAL(18,4) NOT NULL,
    transaction_date  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes             VARCHAR(255)  NULL,
    CONSTRAINT fk_transactions_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_transactions_ticker (ticker_symbol),
    INDEX idx_transactions_user_date (user_id, transaction_date)
) ENGINE=InnoDB;

-- ==========================================================
-- watchlist
-- ==========================================================
CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id        BIGINT      NOT NULL,
    ticker_symbol  VARCHAR(20) NOT NULL,
    added_at       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_watchlist_user_ticker UNIQUE (user_id, ticker_symbol),
    CONSTRAINT fk_watchlist_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_watchlist_ticker (ticker_symbol)
) ENGINE=InnoDB;

-- ==========================================================
-- prediction_history
-- ==========================================================
CREATE TABLE IF NOT EXISTS prediction_history (
    prediction_id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id                  BIGINT        NOT NULL,
    ticker_symbol            VARCHAR(20)   NOT NULL,
    model_name                VARCHAR(50)   NOT NULL,
    predicted_price           DECIMAL(18,4) NOT NULL,
    confidence_score          DECIMAL(5,2)  NULL,
    prediction_horizon_days   INT           NOT NULL DEFAULT 1,
    created_at                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_prediction_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_prediction_ticker (ticker_symbol)
) ENGINE=InnoDB;

-- ==========================================================
-- reports
-- ==========================================================
CREATE TABLE IF NOT EXISTS reports (
    report_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id        BIGINT       NOT NULL,
    report_type    VARCHAR(50)  NOT NULL,
    file_path      VARCHAR(255) NOT NULL,
    generated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reports_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ==========================================================
-- news_cache
-- ==========================================================
CREATE TABLE IF NOT EXISTS news_cache (
    news_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_symbol    VARCHAR(20)   NULL,
    headline         VARCHAR(500)  NOT NULL,
    source           VARCHAR(100)  NULL,
    url              VARCHAR(500)  NOT NULL,
    sentiment_score  DECIMAL(5,4)  NULL,
    published_at     DATETIME      NULL,
    fetched_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_news_ticker_published (ticker_symbol, published_at)
) ENGINE=InnoDB;

-- ==========================================================
-- market_cache
-- ==========================================================
CREATE TABLE IF NOT EXISTS market_cache (
    market_cache_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_symbol    VARCHAR(20)   NOT NULL,
    data_date        DATETIME      NOT NULL,
    open_price       DECIMAL(18,4) NOT NULL,
    high_price       DECIMAL(18,4) NOT NULL,
    low_price        DECIMAL(18,4) NOT NULL,
    close_price      DECIMAL(18,4) NOT NULL,
    volume           BIGINT        NOT NULL DEFAULT 0,
    cached_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_market_ticker_date UNIQUE (ticker_symbol, data_date)
) ENGINE=InnoDB;

-- ==========================================================
-- alerts
-- ==========================================================
CREATE TABLE IF NOT EXISTS alerts (
    alert_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT        NOT NULL,
    ticker_symbol   VARCHAR(20)   NOT NULL,
    condition_type  ENUM('PRICE_ABOVE','PRICE_BELOW','PERCENT_CHANGE') NOT NULL,
    target_value    DECIMAL(18,4) NOT NULL,
    is_triggered    TINYINT(1)    NOT NULL DEFAULT 0,
    is_active       TINYINT(1)    NOT NULL DEFAULT 1,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    triggered_at    DATETIME      NULL,
    CONSTRAINT fk_alerts_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_alerts_ticker (ticker_symbol)
) ENGINE=InnoDB;

-- ==========================================================
-- audit_logs
-- ==========================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id       BIGINT       NULL,
    action        VARCHAR(100) NOT NULL,
    entity_type   VARCHAR(50)  NULL,
    entity_id     BIGINT       NULL,
    ip_address    VARCHAR(45)  NULL,
    details       TEXT         NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL,
    INDEX idx_audit_logs_action (action)
) ENGINE=InnoDB;

-- ==========================================================
-- settings
-- ==========================================================
CREATE TABLE IF NOT EXISTS settings (
    settings_id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id                  BIGINT      NOT NULL,
    theme                    VARCHAR(20) NOT NULL DEFAULT 'light',
    default_currency         VARCHAR(10) NOT NULL DEFAULT 'INR',
    notifications_enabled    TINYINT(1)  NOT NULL DEFAULT 1,
    updated_at               DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_settings_user UNIQUE (user_id),
    CONSTRAINT fk_settings_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ==========================================================
-- password_reset_tokens  (Phase 2 addition)
-- ==========================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  DATETIME     NOT NULL,
    is_used     TINYINT(1)   NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_password_reset_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_password_reset_expires (expires_at)
) ENGINE=InnoDB;

-- ==========================================================
-- login_history  (Phase 2 addition)
-- ==========================================================
CREATE TABLE IF NOT EXISTS login_history (
    login_id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id              BIGINT       NULL,
    username_attempted   VARCHAR(50)  NOT NULL,
    ip_address           VARCHAR(45)  NULL,
    user_agent           VARCHAR(255) NULL,
    status               ENUM('SUCCESS','FAILED') NOT NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_login_history_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL,
    INDEX idx_login_history_user_date (user_id, created_at),
    INDEX idx_login_history_username (username_attempted)
) ENGINE=InnoDB;

-- ==========================================================
-- search_history  (Phase 5 addition)
-- ==========================================================
CREATE TABLE IF NOT EXISTS search_history (
    search_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id        BIGINT       NOT NULL,
    search_query   VARCHAR(255) NOT NULL,
    ticker_symbol  VARCHAR(20)  NULL,
    searched_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_search_history_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_search_history_user_date (user_id, searched_at)
) ENGINE=InnoDB;

-- ==========================================================
-- ipo_listings  (Phase 8 addition)
-- ==========================================================
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

-- ==========================================================
-- notifications  (Phase 8 addition)
-- ==========================================================
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

-- ==========================================================
-- notification_preferences  (Phase 8 addition)
-- ==========================================================
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

-- ==========================================================
-- Seed data: default roles
-- ==========================================================
INSERT INTO roles (role_name, description) VALUES
    ('admin',   'Full administrative access to the platform'),
    ('analyst', 'Elevated access to analytics and reporting tools'),
    ('user',    'Standard end-user access')
ON DUPLICATE KEY UPDATE description = VALUES(description);
