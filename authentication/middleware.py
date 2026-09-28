

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


    @functools.wraps(page_function)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this page.")
            st.stop()
        refresh_session_expiry()
        return page_function(*args, **kwargs)

    return wrapper


def role_required(minimum_role: str) -> Callable:


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


    @functools.wraps(page_function)
    def wrapper(*args, **kwargs):
        if is_authenticated():
            st.info("You are already logged in.")
            st.stop()
        return page_function(*args, **kwargs)

    return wrapper
