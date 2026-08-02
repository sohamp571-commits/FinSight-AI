"""
authentication/logout.py

Purpose: Handles ending a user's session. Kept as its own module (not
folded into session_manager.py) because it's also a Streamlit page --
it renders a short confirmation and clears session state, mirroring
the other page modules in this package.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import end_session, get_current_full_name
from logging_config import logger


@login_required
def render() -> None:
    """Render the Logout confirmation page and clear the active session."""
    full_name = get_current_full_name()
    end_session()
    logger.info("User logged out.")

    st.success(f"You have been logged out{f', {full_name}' if full_name else ''}. See you soon!")
    if st.button("Back to Login", use_container_width=True):
        st.session_state["nav_target"] = "login"
        st.rerun()


def logout_now() -> None:
    """
    Programmatic logout helper for use outside the dedicated page
    (e.g. a "Log out" button in the sidebar of every other page).
    """
    end_session()
    logger.info("User logged out via sidebar action.")
    st.session_state["nav_target"] = "login"
    st.rerun()
