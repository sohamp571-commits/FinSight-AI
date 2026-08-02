# FinSight AI — Folder Structure Reference

```
FinSight-AI/
├── app.py                      # Streamlit entry point: config, routing, sidebar
├── config.py                    # Environment-driven configuration singleton
├── constants.py                 # App-wide constants and enums
├── custom_exceptions.py         # Project exception hierarchy
├── logging_config.py            # Centralized loguru logger setup
├── helper.py                    # Generic formatting/hashing/token helpers
├── utils.py                     # Generic validation utilities
├── requirements.txt             # Pinned Python dependencies
├── README.md                    # Top-level project documentation
├── .gitignore                   # Files/folders excluded from version control
├── .env.example                 # Template for required environment variables
├── .streamlit/
│   └── config.toml               # Streamlit server + base theme configuration
│
├── assets/
│   ├── css/                      # Custom stylesheets (reserved for later phases)
│   ├── images/                   # Static images, incl. uploaded profile pictures
│   └── icons/                    # App icons
│
├── authentication/               # Phase 2 — login, registration, sessions, RBAC
│   ├── __init__.py
│   ├── login.py / register.py / logout.py
│   ├── forgot_password.py / reset_password.py
│   ├── profile.py / change_password.py
│   ├── validators.py             # Field-level validation rules
│   ├── password_utils.py         # Hashing + reset-token helpers
│   ├── session_manager.py        # st.session_state ownership
│   ├── auth_service.py           # Core authentication business logic
│   ├── role_manager.py           # RBAC lookups/permission checks
│   └── middleware.py             # login_required / role_required / guest_only decorators
│
├── database/                     # Phase 1 & 3 — models, connection, service layer
│   ├── __init__.py
│   ├── models.py                 # SQLAlchemy ORM models (source of truth for structure)
│   ├── connection.py              # Engine + session factory (singleton)
│   ├── database.py                # Phase 1 generic DatabaseManager (legacy-compatible)
│   ├── crud.py                    # Stateless, session-scoped CRUD primitives
│   ├── base_service.py            # Generic BaseService[Model] (Phase 3)
│   ├── user_service.py / portfolio_service.py / transaction_service.py
│   ├── watchlist_service.py / prediction_service.py / report_service.py
│   ├── news_service.py / market_cache_service.py / alert_service.py
│   ├── audit_service.py / settings_service.py
│   ├── schema.sql                 # Full DDL reference
│   ├── migration_phase2.sql       # Additive migration for Phase 2 tables/columns
│   └── init_db.py                 # One-shot database initialization script
│
├── dashboard/  stock_search/  analytics/  prediction/  portfolio/
├── watchlist/  news/  chatbot/  reports/  admin/          # Later-phase feature modules
│   └── __init__.py               # Present now so imports/packaging work today
│
├── datasets/  preprocessing/  statistics/  visualization/  # Data-science pipeline modules
│   └── __init__.py
│
├── tests/                        # Automated test suite (scaffolding present)
│   └── __init__.py
│
└── docs/                          # This documentation set
    ├── architecture.md
    ├── database_design.md
    ├── api_design.md
    ├── deployment.md
    ├── coding_standards.md
    ├── developer_guide.md
    ├── user_manual.md
    ├── project_workflow.md
    └── folder_structure.md
```

## Why Empty `__init__.py` Folders Exist Already

Every feature-module folder (`dashboard/`, `analytics/`, `prediction/`, etc.) was scaffolded in Phase 1 with just an `__init__.py` so that:
- The project structure matches the final architecture from day one (nothing to rename/move later)
- `import dashboard` (once populated) works immediately without additional configuration
- PyCharm's package indexing and auto-import features work correctly from the start

These folders remain intentionally empty until the phase that owns them is generated — populating them early would violate the "no placeholder code" rule.
