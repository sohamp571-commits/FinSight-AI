# FinSight AI — Deployment & Environment Guide

## Local Development (PyCharm)

1. Install Python 3.12+ and MySQL 8.0.
2. Open the project root in PyCharm and mark it as **Sources Root** (right-click → Mark Directory as → Sources Root).
3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and fill in real values (see `docs/database_design.md` for schema details and the root `README.md` for the full variable list).
6. Initialize the database:
   ```bash
   python database/init_db.py
   ```
7. Run the app:
   ```bash
   streamlit run app.py
   ```

## MySQL Configuration Notes

- `sql_mode` is forced to `STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE` on every connection (see `database/connection.py`) to catch silent data-truncation bugs early.
- Connection pooling uses `pool_size=DB_POOL_SIZE` (default 10) and `pool_recycle=DB_POOL_RECYCLE` (default 3600s) to avoid MySQL's default 8-hour `wait_timeout` silently dropping idle connections.
- `pool_pre_ping=True` is enabled so a stale connection is detected and replaced automatically rather than surfacing as a runtime error mid-request.

## Environment Variables

All configuration is environment-driven (`config.py`, backed by `python-dotenv`). Never hard-code secrets. Key variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` / `staging` / `production` — gates strict checks like requiring a non-default `SECRET_KEY` |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MySQL connection |
| `DB_POOL_SIZE`, `DB_POOL_RECYCLE` | Connection pool tuning |
| `SECRET_KEY` | Application secret (session signing, future use) |
| `BCRYPT_ROUNDS` | Password hashing cost factor |
| `SESSION_TIMEOUT_MINUTES` | Base session length before "Remember Me" multiplier |
| `LOG_LEVEL`, `LOG_DIR` | Logging verbosity and output location |
| `NEWS_API_KEY` | Reserved for the Phase 7 news module |

## Running in a Different Environment (staging/production)

1. Set `APP_ENV=production` (or `staging`).
2. Set a strong, random `SECRET_KEY` — startup will refuse to run in production with the default dev key (`config.validate()`).
3. Point `DB_HOST`/etc. at the target MySQL instance; ensure the database user has `CREATE`, `ALTER`, `SELECT`, `INSERT`, `UPDATE`, `DELETE` privileges.
4. Run `python database/init_db.py` once against the target database.
5. Serve with `streamlit run app.py --server.port <port> --server.address 0.0.0.0` behind a reverse proxy (e.g. Nginx) with HTTPS termination.
6. Immediately log in as the seeded admin account and change its password (`Admin@12345` is a development-only default — never leave it unchanged in staging/production).

## Logging in Production

Logs write to `logs/app.log` (all levels, 10MB rotation, 30-day retention) and `logs/error.log` (ERROR+, 60-day retention) by default. Point `LOG_DIR` at a persistent volume if deploying in a container, since the working directory's filesystem may not survive restarts.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'config'` | Sources Root not set / running from wrong directory | Mark project root as Sources Root in PyCharm; always run scripts from the project root |
| `DatabaseConnectionError` at startup | MySQL unreachable or wrong credentials | Verify `.env`, confirm MySQL service is running (`mysqladmin ping`) |
| Blank/empty browser tab | Ran with `python app.py` instead of `streamlit run app.py` | Always launch via `streamlit run app.py` |
| `ConfigurationError: SECRET_KEY must be changed` | `APP_ENV=production` with the default dev `SECRET_KEY` | Set a real random `SECRET_KEY` |
| Repeated "Too many failed login attempts" | 5 consecutive failed logins recorded in `login_history` for that user | Wait, or have an admin inspect `login_history` |
| Streamlit "Duplicate widget key" errors while developing | New pages reuse a form/button key already used elsewhere | Ensure every `st.form`/widget on a page has a unique `key=` |
