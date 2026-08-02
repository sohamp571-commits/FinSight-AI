-- ==========================================================
-- FinSight AI - Phase 5 Migration
-- Run this ONLY if your database was already initialized before
-- Phase 5. It adds the search_history table in place, without
-- dropping or recreating any existing table.
--
-- If you have NOT initialized the database yet, just run the updated
-- database/schema.sql (or database/init_db.py) instead -- both
-- already include this table.
-- ==========================================================

USE finsight_ai;

CREATE TABLE IF NOT EXISTS search_history (
    search_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id        BIGINT       NOT NULL,
    search_query   VARCHAR(255) NOT NULL,
    ticker_symbol  VARCHAR(20)  NULL,
    searched_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_search_history_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    INDEX idx_search_history_user_date (user_id, searched_at)
) ENGINE=InnoDB;
