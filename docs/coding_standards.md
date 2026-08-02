# FinSight AI — Coding Standards

## General

- Follow **PEP 8** throughout; 4-space indentation, no tabs.
- Every module opens with a docstring explaining its **Purpose**.
- Every public function/method has a docstring (Google-style: `Args:` / `Returns:` / `Raises:`).
- Type hints are mandatory on all function signatures (`Python 3.12+` syntax, e.g. `str | None` instead of `Optional[str]`).
- No bare `except:` — always catch a specific exception type, and prefer catching `FinSightBaseException` subclasses or `SQLAlchemyError` over generic `Exception`, except at true top-level boundaries (`app.py`'s `main()`, `init_db.py`'s `run_initialization()`).
- No placeholder code, no `TODO` comments left in committed files — incomplete work is called out explicitly in docstrings/README instead (e.g. `profile_picture` column decision, or a module reserved for a later phase).

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Modules/files | `snake_case.py` | `auth_service.py` |
| Classes | `PascalCase` | `AuthService`, `BaseService` |
| Functions/methods | `snake_case` | `get_by_id`, `create_user` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_LOGIN_ATTEMPTS` |
| Private helpers | leading underscore | `_render_sidebar`, `_is_locked_out` |
| SQLAlchemy models | singular `PascalCase`, plural `__tablename__` | `class User: __tablename__ = "users"` |
| Primary key columns | `<table_singular>_id` | `user_id`, `portfolio_id` |
| Service singletons | `snake_case`, same name as module | `user_service = UserService()` |

## Layering Rules (enforced by convention, not tooling)

1. `constants.py`, `custom_exceptions.py`, `config.py`, `logging_config.py`, `helper.py`, `utils.py` never import anything else from the project — they are the dependency floor.
2. `database/models.py` and `database/connection.py` may only import the floor modules above.
3. `database/crud.py` may only import `database/models.py`.
4. `database/base_service.py` may only import `database/crud.py`, `database/connection.py`, floor modules.
5. Domain services (`database/*_service.py`) may import `base_service.py`, `crud.py`, `connection.py`, `models.py`, floor modules — never each other's private internals, and never Streamlit.
6. `authentication/*` may import `database/*` and floor modules, plus Streamlit for page modules only (`login.py`, `register.py`, ...) — never the other way around.
7. `app.py` is the only module allowed to import both `authentication/*` page modules and (in later phases) other feature-module page functions, to assemble routing.

This keeps the import graph acyclic and is exactly why, for example, `database/user_service.py` never imports `authentication.password_utils` — that would violate rule 5/6 and create a cycle with `authentication.auth_service` (which imports `database.database`).

## Exception Handling Pattern

```python
try:
    with db_connection.get_session() as session:
        ...
except IntegrityError as exc:
    raise DuplicateRecordError("...") from exc
except SQLAlchemyError as exc:
    logger.error(f"...: {exc}")
    raise DatabaseQueryError(str(exc)) from exc
```
Always log before raising a translated exception (once, at the point of translation) — never log the same error again further up the call stack, to avoid duplicate noisy log lines.

## Logging Pattern

Use `from logging_config import logger` everywhere; never `import logging` directly or instantiate a new logger. Log levels:
- `logger.info` — normal business events (user created, order placed, session started)
- `logger.warning` — recoverable/expected failure paths (duplicate record rejected, locked-out login attempt)
- `logger.error` — unexpected failures that were caught and handled
- `logger.exception` — only in true top-level handlers, to capture the full traceback

## Dependency Rationale (`requirements.txt`)

| Package | Why |
|---|---|
| `streamlit` | Rapid, pure-Python UI without a separate frontend build step |
| `SQLAlchemy` + `PyMySQL` | ORM + pure-Python MySQL driver (no C build dependency, easier on Windows/PyCharm) |
| `pandas` / `numpy` / `scipy` | Core data manipulation and statistics for the CIPAT syllabus requirements |
| `plotly` / `matplotlib` | Interactive and static charting |
| `scikit-learn` / `xgboost` | ML models for the Phase 6 prediction module |
| `yfinance` | Free market data source for OHLCV history |
| `newsapi-python` / `textblob` / `nltk` | News sentiment pipeline (Phase 7) |
| `reportlab` / `openpyxl` | PDF and Excel report generation (Phase 8) |
| `bcrypt` / `passlib` | Industry-standard adaptive password hashing |
| `python-dotenv` | 12-factor style configuration from `.env` |
| `loguru` | Simpler, more capable logging API than the stdlib `logging` module |
