

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

    end_session()
    logger.info("User logged out via sidebar action.")
    st.session_state["nav_target"] = "login"
    st.rerun()
