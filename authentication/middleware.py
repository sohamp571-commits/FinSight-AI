"""
authentication/middleware.py

Purpose: Reusable decorators that guard Streamlit "pages" (the
top-level render function of each page module). Since Streamlit has
no routing layer of its own, these decorators are how FinSight AI
enforces "you must be logged in" / "you must be an admin" rules
consistently across every page, instead of copy-pasting session
checks into each one.
"""

import functools
from typing import Callable

import streamlit as st

from authentication.role_manager import has_minimum_role
from authentication.session_manager import (
    get_current_role,
    is_authenticated,
    refresh_session_expiry,
)
from logging_config import logger


def login_required(page_function: Callable) -> Callable:
    """
    Decorator that stops a Streamlit page from rendering unless the
    current session is authenticated. Redirects the user to a
    friendly "please log in" message instead of raising.

    Usage:
        @login_required
        def render():
            st.write("secret dashboard content")
    """

    @functools.wraps(page_function)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this page.")
            st.stop()
        refresh_session_expiry()
        return page_function(*args, **kwargs)

    return wrapper


def role_required(minimum_role: str) -> Callable:
    """
    Decorator factory that stops a Streamlit page from rendering unless
    the current user's role meets or exceeds `minimum_role`.

    Usage:
        @role_required("admin")
        def render():
            st.write("admin-only content")
    """

    def decorator(page_function: Callable) -> Callable:
        @functools.wraps(page_function)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                st.warning("Please log in to access this page.")
                st.stop()

            current_role = get_current_role()
            if not has_minimum_role(current_role, minimum_role):
                logger.warning(
                    f"Access denied: role='{current_role}' attempted a "
                    f"'{minimum_role}'-only page."
                )
                st.error("You do not have permission to view this page.")
                st.stop()

            refresh_session_expiry()
            return page_function(*args, **kwargs)

        return wrapper

    return decorator


def guest_only(page_function: Callable) -> Callable:
    """
    Decorator for pages that should only be visible to logged-out
    visitors (e.g. Login, Register). Redirects already-authenticated
    users away with a friendly notice.

    Usage:
        @guest_only
        def render():
            st.write("login form")
    """

    @functools.wraps(page_function)
    def wrapper(*args, **kwargs):
        if is_authenticated():
            st.info("You are already logged in.")
            st.stop()
        return page_function(*args, **kwargs)

    return wrapper
