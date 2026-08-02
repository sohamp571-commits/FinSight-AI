# FinSight AI — Architecture

## Layered Overview

FinSight AI follows a strict four-layer architecture. Each layer only talks to the layer directly below it — pages never touch SQLAlchemy directly, and services never touch Streamlit.

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer (Streamlit pages)                    │
│  authentication/login.py, register.py, profile.py, ...   │
│  (later: dashboard/, portfolio/, analytics/, ...)         │
└───────────────────────┬───────────────────────────────────┘
                         │ calls
┌───────────────────────▼───────────────────────────────────┐
│  Business Logic Layer (services)                          │
│  authentication/auth_service.py                           │
│  database/user_service.py, portfolio_service.py, ...      │
└───────────────────────┬───────────────────────────────────┘
                         │ calls
┌───────────────────────▼───────────────────────────────────┐
│  Data Access Layer                                         │
│  database/base_service.py  (session mgmt + CRUD contract)  │
│  database/crud.py          (stateless SQL primitives)      │
│  database/connection.py    (engine + session factory)      │
└───────────────────────┬───────────────────────────────────┘
                         │ SQL
┌───────────────────────▼───────────────────────────────────┐
│  MySQL 8.0                                                  │
└─────────────────────────────────────────────────────────────┘
```

Cross-cutting concerns (`config.py`, `logging_config.py`, `custom_exceptions.py`, `constants.py`, `helper.py`, `utils.py`) are imported by every layer and never import application code themselves — this keeps the dependency graph acyclic.

## Request Lifecycle (example: user logs in)

1. `app.py` renders `authentication/login.py` because no session exists.
2. The form submits → `AuthService.authenticate()` is called.
3. `AuthService` calls `database.database.db_manager` (Phase 1 generic manager) and `database.models.User` to look up the account.
4. On success, `authentication/session_manager.start_session()` writes to `st.session_state`.
5. `app.py` reruns and `_route()` now sends the user to the dashboard placeholder / sidebar.

## Session Model

Streamlit has no server-side session store, so `authentication/session_manager.py` is the single source of truth for "is this browser tab logged in" via `st.session_state`. Every page that requires auth is wrapped in the `@login_required` / `@role_required(...)` decorators from `authentication/middleware.py`.

## Service Layer Design

Every table has exactly one owning service (e.g. `portfolio_service.py` owns `portfolio`). Services either:
- Subclass `BaseService[Model]` for full generic CRUD + pagination/filter/search/sort, or
- Use `database/crud.py` primitives directly inside their own session when an operation must be atomic across two tables (see `transaction_service.buy_stock`/`sell_stock`, which write to both `transactions` and `portfolio` in one transaction).

## Error Handling Strategy

All custom exceptions inherit from `FinSightBaseException` (`custom_exceptions.py`). Each layer catches only the exceptions it can meaningfully add context to, then re-raises or translates:
- `crud.py` raises nothing — it lets SQLAlchemy exceptions bubble up.
- `base_service.py` / domain services catch `SQLAlchemyError` and translate to `DatabaseQueryError`, `DuplicateRecordError`, or `RecordNotFoundError`.
- Streamlit pages catch `FinSightBaseException` subclasses and render `st.error`/`st.warning`; anything unexpected is caught by `app.py`'s top-level handler and logged via `logger.exception`.

## Logging Strategy

`logging_config.py` configures a single loguru logger with three sinks: colorized console output, a rotating `logs/app.log` (all levels), and a rotating `logs/error.log` (ERROR+ only, with tracebacks). Every service logs on create/update/delete and on caught exceptions.
