# FinSight AI — Developer Guide

This guide is for extending FinSight AI in later phases (dashboard, analytics, prediction, etc.) while staying consistent with the existing architecture.

## Adding a New Feature Module (e.g. `dashboard/`)

1. The folder and its `__init__.py` already exist from Phase 1 scaffolding.
2. If the feature needs a new table, add the SQLAlchemy model to `database/models.py`, the DDL to `database/schema.sql`, and a migration file (`database/migration_phaseN.sql`) — do **not** edit prior migration files.
3. Create `database/<feature>_service.py` subclassing `BaseService[YourModel]` (see any existing `*_service.py` for the pattern) — this is your only way to touch the database from the new module.
4. Create the Streamlit page module(s) inside the feature folder, e.g. `dashboard/overview.py`, with a `render()` function as the entry point, decorated with `@login_required` or `@role_required("...")` from `authentication.middleware`.
5. Register the new page in `app.py`'s `AUTHENTICATED_PAGES` dict and add a sidebar button in `_render_sidebar()`.

## Example: Calling a Service From a Page

```python
# dashboard/overview.py
import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from database.portfolio_service import portfolio_service
from custom_exceptions import FinSightBaseException
from logging_config import logger


@login_required
def render() -> None:
    user_id = get_current_user_id()
    try:
        summary = portfolio_service.portfolio_summary(user_id)
        st.metric("Total Invested", f"₹{summary['total_invested']:,.2f}")
        st.metric("Current Value", f"₹{summary['total_current_value']:,.2f}")
    except FinSightBaseException as exc:
        logger.error(f"Failed to load portfolio summary: {exc}")
        st.error("Could not load your portfolio right now.")
```

## Adding a New Service Method

Follow the existing pattern in any `database/*_service.py`:
1. Validate inputs first (raise `ValidationError` immediately, before touching the database).
2. Use inherited `BaseService` methods (`self.create`, `self.update`, `self.list`, ...) wherever plain CRUD suffices.
3. Only drop into a manual `db_connection.get_session()` block (using `database/crud.py` functions) when the operation must be atomic across more than one table — see `transaction_service.buy_stock` for the reference implementation.
4. Log the outcome with `logger.info`/`logger.warning` at the end of the method.

## Running Tests

```bash
pip install pytest
pytest tests/
```
(Test suite scaffolding lands in a later phase; `tests/__init__.py` is already present.)

## Debugging Tips

- Set `LOG_LEVEL=DEBUG` in `.env` for verbose console output.
- Check `logs/app.log` and `logs/error.log` for anything that didn't surface in the UI.
- Use `python database/init_db.py` any time you need a clean re-verification of connectivity/tables — it's fully idempotent and safe to re-run.
- If PyCharm reports unresolved imports for top-level modules like `config` or `constants`, re-confirm the project root is marked as **Sources Root**.

## Style Checklist Before Committing a New File

- [ ] Module docstring with a "Purpose" explanation
- [ ] Type hints on every function signature
- [ ] No bare `except:`
- [ ] Uses `logger` from `logging_config`, not `print()` (except user-facing CLI scripts like `init_db.py`)
- [ ] Raises `custom_exceptions` types, not generic `Exception`
- [ ] No hard-coded secrets/credentials
- [ ] Follows the import-layering rules in `docs/coding_standards.md`
