# FinSight AI

**AI-Powered Stock Market Intelligence & Portfolio Analytics Platform**

A BE Computer Engineering (Python for Data Science, CIPAT) project inspired by Yahoo Finance, TradingView, Zerodha, Groww, and Bloomberg — built entirely with Python, Streamlit, and MySQL.

---

## Project Overview

FinSight AI is a full-stack, enterprise-style stock market analytics platform. It combines a normalized MySQL database, a layered SQLAlchemy service architecture, secure role-based authentication, and a Streamlit front end into a single, self-contained Python project designed to run cleanly inside PyCharm.

The project is being built in phases:

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Foundation (config, logging, database layer, schema) | ✅ Complete |
| 2 | Authentication & User Management | ✅ Complete |
| 3 | Database Services & CRUD | ✅ Complete |
| 4+ | Dashboard, analytics, predictions, portfolio, news, reports, admin | 🔜 Planned |

## Features

**Implemented today:**
- Secure registration, login, logout, "remember me", and session management
- Forgot password / reset password via single-use, time-limited tokens
- Change password, profile editing, profile picture upload
- Role-based access control (admin / analyst / user)
- Login history tracking and brute-force lockout
- Soft delete / restore for user accounts
- Full CRUD + pagination/filtering/searching/sorting service layer for every table
- Portfolio holdings with weighted-average cost basis
- Atomic buy/sell transaction ledger
- Watchlist, price/percent-change alerts, settings (theme/currency/notifications)
- Centralized logging, configuration, and exception handling

**Planned in later phases:**
- Live dashboard with charts and KPIs
- ML-based price prediction (Scikit-Learn / XGBoost)
- News sentiment analysis (NewsAPI + TextBlob)
- PDF/Excel report generation
- Admin panel

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | Python 3.12+ |
| Database | MySQL 8.0 |
| ORM | SQLAlchemy 2.0 |
| Data | Pandas, NumPy, SciPy |
| Visualization | Plotly, Matplotlib |
| ML | Scikit-Learn, XGBoost |
| Market Data | yfinance |
| News/NLP | NewsAPI, TextBlob, NLTK |
| Reporting | ReportLab, OpenPyXL |
| Security | bcrypt, passlib |
| Config | python-dotenv |
| Logging | loguru |

## Folder Structure

```
FinSight-AI/
├── app.py                   # Streamlit entry point (routing, sidebar, session bootstrap)
├── config.py                 # Environment-driven configuration singleton
├── constants.py               # App-wide constants and enums
├── custom_exceptions.py       # Project exception hierarchy
├── logging_config.py          # Centralized loguru setup
├── helper.py / utils.py       # Generic helpers and validators
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/config.toml     # Streamlit theme/server config
├── assets/                    # css / images / icons
├── authentication/            # Login, register, sessions, RBAC (Phase 2)
├── database/                  # Models, connection, CRUD services (Phase 1 & 3)
├── dashboard/  analytics/  prediction/  portfolio/  watchlist/
├── news/  chatbot/  reports/  admin/                # Later phases
├── datasets/  preprocessing/  statistics/  visualization/
├── tests/
└── docs/                       # Architecture & developer documentation
```

See `docs/folder_structure.md` for a full description of every folder's responsibility.

## Installation

### Prerequisites
- Python 3.12+
- MySQL 8.0 (running locally or reachable over the network)
- PyCharm Community or Professional
- Git

### 1. Clone / Open the Project
Open the `FinSight-AI` folder directly in PyCharm (`File → Open`).

## PyCharm Setup

1. `File → Open` and select the `FinSight-AI` folder.
2. PyCharm will detect `requirements.txt` — accept the prompt to create a virtual environment, or create one manually (see below).
3. Right-click the `FinSight-AI` root folder → **Mark Directory as → Sources Root** so all top-level imports (`config`, `database.models`, `authentication.login`, ...) resolve correctly.
4. Set the Python interpreter to the project's `venv` under **Settings → Project → Python Interpreter**.

## Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

## Requirements

```bash
pip install -r requirements.txt
```

All dependency versions are pinned in `requirements.txt`. See `docs/coding_standards.md` for why each package was chosen.

## Database Setup

1. Ensure MySQL 8.0 is running and you have a user with permission to create databases.
2. Copy `.env.example` to `.env` and fill in your MySQL credentials (see below).
3. From the project root, run the initialization script:

```bash
python database/init_db.py
```

This will:
- Create the `finsight_ai` database if it doesn't exist
- Create every table from the SQLAlchemy models
- Seed the default roles (`admin`, `analyst`, `user`)
- Create a default admin account (`admin` / `Admin@12345` — **change this immediately**)

If you prefer to run the raw SQL DDL directly (e.g. in MySQL Workbench), use `database/schema.sql` instead — it is functionally equivalent and includes explicit `ENUM` types and indexes.

## How to Configure .env

```bash
cp .env.example .env
```

Then edit `.env`:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=finsight_ai
DB_USER=root
DB_PASSWORD=your_mysql_password_here
SECRET_KEY=change-this-to-a-random-64-character-string
```

Never commit your real `.env` file — it's excluded via `.gitignore`.

## How to Run

```bash
streamlit run app.py
```

Streamlit will open the app at `http://localhost:8501`. Log in with the seeded admin account or register a new user.

> **Note:** Streamlit apps must be launched with `streamlit run app.py`, not `python app.py` — the latter will execute the script but without the Streamlit server/runtime, so no UI will render.

## Screenshots

_Screenshots will be added here once the dashboard (Phase 4) is complete._

`assets/images/screenshots/login.png`
`assets/images/screenshots/dashboard.png`

## Project Architecture

See `docs/architecture.md` for the full breakdown. In short:

```
Streamlit Pages  →  Domain Services  →  BaseService/crud.py  →  SQLAlchemy Session  →  MySQL
        ↑                                        ↓
   session_manager.py                    logging_config.py / custom_exceptions.py
```

## Future Modules

- **Phase 4:** Dashboard, stock search, market data ingestion (yfinance)
- **Phase 5:** Analytics & statistics (Pandas/NumPy/SciPy pipelines)
- **Phase 6:** ML price prediction (Scikit-Learn / XGBoost)
- **Phase 7:** News sentiment (NewsAPI / TextBlob / NLTK)
- **Phase 8:** PDF/Excel reports (ReportLab / OpenPyXL)
- **Phase 9:** Admin panel
- **Phase 10:** Testing, deployment, polish

## Common Errors & Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'config'` | Project root not marked as Sources Root | Right-click root → Mark Directory as → Sources Root |
| `DatabaseConnectionError` on startup | MySQL not running, or wrong `.env` credentials | Check `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`; confirm MySQL is running |
| Blank page / nothing renders | Ran `python app.py` instead of `streamlit run app.py` | Always launch via `streamlit run app.py` |
| `Access denied for user` (MySQL) | Incorrect password or missing privileges | Verify credentials with `mysql -u <user> -p`; grant `ALL PRIVILEGES` if needed |
| `ConfigurationError: SECRET_KEY must be changed` | Running with `APP_ENV=production` and default `SECRET_KEY` | Set a strong random `SECRET_KEY` in `.env` |

More troubleshooting detail lives in `docs/deployment.md`.

## Contributing

This is an academic (CIPAT) project developed phase-by-phase. Contributions follow the same architecture and conventions documented in `docs/coding_standards.md` and `docs/developer_guide.md` — new feature modules should reuse the existing `database/*_service.py` pattern rather than querying the database directly.

## License

This project is developed for academic purposes as part of a Third Year BE Computer Engineering curriculum (Python for Data Science, CIPAT). All rights reserved by the author unless otherwise licensed.
