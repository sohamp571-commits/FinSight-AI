-- ==========================================================
-- FinSight AI - Phase 2 Migration
-- Run this ONLY if your database was already initialized from the
-- Phase 1 schema.sql. It adds the auth-related additions in place,
-- without dropping or recreating any existing table.
--
-- If you have NOT initialized the database yet, just run the updated
-- database/schema.sql instead -- it already includes these changes.
-- ==========================================================

USE finsight_ai;

-- Add soft-delete column to users (safe no-op if it already exists)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL AFTER is_active;

-- password_reset_tokens
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

-- login_history
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
