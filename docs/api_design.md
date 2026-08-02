# FinSight AI — Internal "API" Design

FinSight AI has no REST/HTTP API in this phase — Streamlit pages call Python service classes directly in-process. This document describes that internal contract, which plays the same role a REST API spec would in a client-server app.

## Design Principles

- Every service method either **returns a value** or **raises a `FinSightBaseException` subclass** — never both silently swallowed nor an unhandled stack trace.
- Read methods that can legitimately return "nothing" use `Optional[...]` (e.g. `find_by_email`); read methods that represent "the caller expected this to exist" raise `RecordNotFoundError` instead (e.g. `get_by_id`).
- List/search endpoints all share the same return shape: `{"items": [...], "total": int, "page": int, "page_size": int, "total_pages": int}`.

## Authentication Service (`authentication.auth_service.AuthService`)

| Method | Description |
|---|---|
| `register_user(full_name, email, username, password, confirm_password)` | Create a new account with the default `user` role |
| `authenticate(username_or_email, password, ip_address="", user_agent="")` | Verify credentials, record login history, return the `User` |
| `request_password_reset(email)` | Issue a reset token, return raw token or `None` |
| `reset_password(raw_token, new_password, confirm_password)` | Consume a token and set a new password |
| `change_password(user_id, current_password, new_password, confirm_password)` | Change password for a logged-in user |
| `get_profile(user_id)` / `update_profile(user_id, full_name, email)` | Read/update profile fields |
| `deactivate_account` / `reactivate_account` / `soft_delete_account` | Account status management |

## Generic CRUD Contract (`database.base_service.BaseService[Model]`)

| Method | Description |
|---|---|
| `create(instance)` | Insert one record |
| `bulk_create(instances)` | Insert many records in one transaction |
| `get_by_id(record_id)` | Fetch by primary key, raises `RecordNotFoundError` |
| `find_one_by(**filters)` | Fetch by exact-match filters, returns `None` if absent |
| `list(filters, search_term, search_columns, sort_by, sort_direction, page, page_size)` | Paginated, filtered, searched, sorted list |
| `count(filters)` | Row count |
| `update(record_id, updates: dict)` | Partial update by primary key |
| `delete(record_id)` | Hard delete by primary key |

## Domain Services

Each domain service extends the contract above with business methods. See `docs/developer_guide.md` for a full call-through example, and inline docstrings in each `database/*_service.py` file for the authoritative, up-to-date signature list:

- `user_service.py` — `create_user`, `find_by_email`, `find_by_username`, `soft_delete`, `restore`
- `portfolio_service.py` — `add_stock`, `remove_stock`, `portfolio_summary`
- `transaction_service.py` — `buy_stock`, `sell_stock`, `transaction_history`, `search_transactions`
- `watchlist_service.py` — `add_stock`, `remove_stock`, `list_watchlist`
- `alert_service.py` — `create_alert`, `update_alert`, `activate`, `deactivate`, `evaluate_and_trigger`
- `settings_service.py` — `get_or_create`, `set_theme`, `set_currency`, `set_notifications`

## Future: Public REST API

If FinSight AI is ever exposed outside Streamlit (e.g. a mobile client), this internal service layer is designed to be wrapped by a thin FastAPI/Flask layer without modification — every service method already returns plain Python objects/dicts and raises typed exceptions that map cleanly to HTTP status codes (`RecordNotFoundError` → 404, `ValidationError` → 400, `DuplicateRecordError` → 409, `AuthenticationError` → 401, `AuthorizationError` → 403).
