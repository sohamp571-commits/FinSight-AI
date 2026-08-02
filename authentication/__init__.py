"""
authentication package

Enterprise-grade authentication and user-management module for
FinSight AI. Built on top of the Phase 1 foundation (config, logging,
database, custom_exceptions, helper, utils).

Sub-modules:
    validators.py       - email/username/password format validation
    password_utils.py   - hashing, reset-token generation/verification
    session_manager.py  - Streamlit session-state + "remember me" handling
    role_manager.py     - role lookups and permission checks
    auth_service.py     - core business logic (register/login/reset/etc.)
    middleware.py        - route-guard decorators for Streamlit pages
    login.py / register.py / logout.py / forgot_password.py /
    reset_password.py / profile.py / change_password.py
                          - Streamlit page UIs
"""

from authentication.auth_service import AuthService

__all__ = ["AuthService"]
