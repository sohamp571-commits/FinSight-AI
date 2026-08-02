"""
authentication/session_manager.py

Purpose: Owns all reads/writes to Streamlit's `st.session_state` for
authentication concerns (current user, role, session expiry, "remember
me" token). Streamlit has no server-side session store, so this module
is the single place that defines what "being logged in" means for the
rest of the app -- every other module should go through here instead
of touching st.session_state directly.
"""

from datetime import datetime, timedelta
from typing import Any

import streamlit as st

from config import config
from logging_config import logger

SESSION_KEY_USER_ID = "auth_user_id"
SESSION_KEY_USERNAME = "auth_username"
SESSION_KEY_FULL_NAME = "auth_full_name"
SESSION_KEY_ROLE = "auth_role"
SESSION_KEY_EXPIRES_AT = "auth_expires_at"
SESSION_KEY_REMEMBER_TOKEN = "auth_remember_token"


def start_session(user_id: int, username: str, full_name: str, role_name: str, remember_me: bool = False) -> None:
    """
    Populate st.session_state after a successful login.

    Args:
        user_id: Primary key of the authenticated user.
        username: The user's username, cached for display without a DB hit.
        full_name: The user's display name.
        role_name: The user's role (admin/analyst/user), used for authorization checks.
        remember_me: If True, extends the session timeout window.
    """
    timeout_minutes = config.SESSION_TIMEOUT_MINUTES * (24 * 30 if remember_me else 1)

    st.session_state[SESSION_KEY_USER_ID] = user_id
    st.session_state[SESSION_KEY_USERNAME] = username
    st.session_state[SESSION_KEY_FULL_NAME] = full_name
    st.session_state[SESSION_KEY_ROLE] = role_name
    st.session_state[SESSION_KEY_EXPIRES_AT] = datetime.utcnow() + timedelta(minutes=timeout_minutes)

    logger.info(f"Session started for user_id={user_id} (remember_me={remember_me})")


def end_session() -> None:
    """Clear all authentication-related keys from session state (logout)."""
    user_id = st.session_state.get(SESSION_KEY_USER_ID)
    for key in (
        SESSION_KEY_USER_ID,
        SESSION_KEY_USERNAME,
        SESSION_KEY_FULL_NAME,
        SESSION_KEY_ROLE,
        SESSION_KEY_EXPIRES_AT,
        SESSION_KEY_REMEMBER_TOKEN,
    ):
        st.session_state.pop(key, None)
    logger.info(f"Session ended for user_id={user_id}")


def is_authenticated() -> bool:
    """Return True if a non-expired, logged-in session currently exists."""
    if SESSION_KEY_USER_ID not in st.session_state:
        return False

    expires_at = st.session_state.get(SESSION_KEY_EXPIRES_AT)
    if expires_at is None or datetime.utcnow() > expires_at:
        end_session()
        return False

    return True


def get_current_user_id() -> int | None:
    """Return the currently authenticated user's ID, or None."""
    return st.session_state.get(SESSION_KEY_USER_ID) if is_authenticated() else None


def get_current_username() -> str | None:
    """Return the currently authenticated user's username, or None."""
    return st.session_state.get(SESSION_KEY_USERNAME) if is_authenticated() else None


def get_current_full_name() -> str | None:
    """Return the currently authenticated user's display name, or None."""
    return st.session_state.get(SESSION_KEY_FULL_NAME) if is_authenticated() else None


def get_current_role() -> str | None:
    """Return the currently authenticated user's role, or None."""
    return st.session_state.get(SESSION_KEY_ROLE) if is_authenticated() else None


def refresh_session_expiry() -> None:
    """Slide the session expiry forward on user activity (call from page guards)."""
    if is_authenticated():
        st.session_state[SESSION_KEY_EXPIRES_AT] = datetime.utcnow() + timedelta(
            minutes=config.SESSION_TIMEOUT_MINUTES
        )


def get_session_snapshot() -> dict[str, Any]:
    """Return a read-only snapshot of the current auth session, for logging/debugging."""
    return {
        "user_id": st.session_state.get(SESSION_KEY_USER_ID),
        "username": st.session_state.get(SESSION_KEY_USERNAME),
        "role": st.session_state.get(SESSION_KEY_ROLE),
        "expires_at": st.session_state.get(SESSION_KEY_EXPIRES_AT),
    }
