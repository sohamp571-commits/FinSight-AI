"""
authentication/change_password.py

Purpose: Streamlit page for an already-authenticated user to change
their password by confirming their current one. Distinct from
reset_password.py, which is for logged-out users using an emailed
token.
"""

import streamlit as st

from custom_exceptions import AuthenticationError, ValidationError
from logging_config import logger

from authentication.auth_service import AuthService
from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id


@login_required
def render() -> None:
    """Render the Change Password page. Entry point called from app.py's router."""
    st.markdown("### Change your password")
    st.caption("Enter your current password and choose a new one.")

    user_id = get_current_user_id()

    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password", placeholder="At least 8 characters")
        confirm_password = st.text_input("Confirm New Password", type="password")
        st.caption("Password must be at least 8 characters and include a letter and a number.")
        submitted = st.form_submit_button("Update Password", use_container_width=True)

    if submitted:
        try:
            AuthService.change_password(user_id, current_password, new_password, confirm_password)
            st.success("Your password has been updated successfully.")
        except AuthenticationError as exc:
            st.error(exc.message)
        except ValidationError as exc:
            st.warning(exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error during change password: {exc}")
            st.error("Something went wrong while updating your password. Please try again.")
