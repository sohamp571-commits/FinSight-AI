# FinSight AI — Database Design

## Engine & Conventions

- MySQL 8.0, InnoDB engine, `utf8mb4` charset throughout.
- Every table has a surrogate integer primary key (`<table>_id`), `created_at`/`updated_at` timestamps where mutable, and explicit foreign keys with an appropriate `ON DELETE` policy.
- Money/quantity fields use `DECIMAL(18,4)` — never `FLOAT`/`DOUBLE` — to avoid floating-point rounding errors in financial calculations.

## Entity-Relationship Summary

```
roles (1) ───< (many) users
users (1) ───< (many) portfolio
users (1) ───< (many) transactions
users (1) ───< (many) watchlist
users (1) ───< (many) prediction_history
users (1) ───< (many) reports
users (1) ───< (many) alerts
users (1) ───< (many) audit_logs
users (1) ───1 settings
users (1) ───< (many) password_reset_tokens
users (1) ───< (many) login_history

news_cache     — independent, optionally tagged with ticker_symbol
market_cache   — independent, keyed by (ticker_symbol, data_date)
```

## Table Reference

| Table | Purpose | Key Constraints |
|---|---|---|
| `roles` | RBAC role definitions (admin/analyst/user) | unique `role_name` |
| `users` | Account records | unique `email`, `username`; FK → `roles` |
| `portfolio` | Current holdings (one row per user+ticker) | unique `(user_id, ticker_symbol)` |
| `transactions` | Append-only buy/sell ledger | FK → `users`, cascade delete |
| `watchlist` | Tracked tickers per user | unique `(user_id, ticker_symbol)` |
| `prediction_history` | Logged ML prediction outputs | FK → `users` |
| `reports` | Metadata for generated PDF/Excel files | FK → `users` |
| `news_cache` | Cached news headlines + sentiment | indexed on `(ticker_symbol, published_at)` |
| `market_cache` | Cached daily OHLCV bars | unique `(ticker_symbol, data_date)` |
| `alerts` | User-defined price/percent alerts | FK → `users` |
| `audit_logs` | Structured security/action audit trail | FK → `users` (`SET NULL` on delete) |
| `settings` | Per-user preferences (theme, currency, notifications) | unique `user_id` |
| `password_reset_tokens` | Single-use, expiring password reset tokens | unique `token_hash` |
| `login_history` | Every login attempt, success or failure | FK → `users` (`SET NULL` on delete) |

## Why `password_reset_tokens` and `login_history` Were Added in Phase 2

Phase 1's schema had no mechanism for issuing a revocable, time-limited secret separate from a session (`password_reset_tokens`), and `users.last_login_at` only records the single most recent login rather than a full auditable history with IP/status (`login_history`). Both were added as pure additions — no Phase 1 table was altered except `users.deleted_at` (soft delete support).

## Soft Delete Strategy

`users.deleted_at` (nullable `DATETIME`) marks an account as soft-deleted without removing the row or cascading deletes to historical data (transactions, audit logs, etc. must survive account deletion for compliance). `is_active` remains a separate, reversible "temporarily disabled" flag — the two are intentionally independent.

## Indexing Strategy

Indexes are placed on every foreign key, every column used in frequent lookups (`ticker_symbol` across nearly every table), and every column used for chronological sorting (`created_at`, `transaction_date`, `published_at`). Composite unique constraints (e.g. `(user_id, ticker_symbol)` on `portfolio`/`watchlist`) enforce business rules at the database level, not just in application code.

## Migration Files

- `database/schema.sql` — full DDL, source of truth for manual/DBA execution.
- `database/migration_phase2.sql` — additive `ALTER`/`CREATE` statements for databases already initialized before Phase 2.
- `database/init_db.py` — programmatic initialization via `SQLAlchemy`'s `Base.metadata.create_all()`, used for local development.
