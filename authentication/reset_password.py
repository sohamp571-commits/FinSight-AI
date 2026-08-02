"""
authentication/reset_password.py

Purpose: Streamlit page where a user lands after clicking the link
from forgot_password.py. Reads the raw reset token from the URL query
parameters, lets the user set a new password, and consumes the token
via AuthService.reset_password().
"""

import streamlit as st

from custom_exceptions import AuthenticationError, ValidationError
from logging_config import logger

from authentication.auth_service import AuthService
from authentication.middleware import guest_only


@guest_only
def render() -> None:
    """Render the Reset Password page. Entry point called from app.py's router."""
    st.markdown("### Reset your password")

    query_params = st.query_params
    token_from_url = query_params.get("token", "")

    with st.form("reset_password_form"):
        token = st.text_input(
            "Reset Token",
            value=token_from_url,
            help="This is pre-filled automatically when you arrive via your reset link.",
        )
        new_password = st.text_input("New Password", type="password", placeholder="At least 8 characters")
        confirm_password = st.text_input("Confirm New Password", type="password")
        st.caption("Password must be at least 8 characters and include a letter and a number.")
        submitted = st.form_submit_button("Reset Password", use_container_width=True)

    if submitted:
        if not token.strip():
            st.warning("Please provide the reset token from your email link.")
            return
        try:
            AuthService.reset_password(token.strip(), new_password, confirm_password)
            st.success("Your password has been reset successfully. You can now log in.")
            st.session_state["nav_target"] = "login"
            st.rerun()
        except AuthenticationError as exc:
            st.error(exc.message)
        except ValidationError as exc:
            st.warning(exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error during password reset: {exc}")
            st.error("Something went wrong while resetting your password. Please try again.")

    st.markdown("---")
    if st.button("Back to Login", use_container_width=True):
        st.session_state["nav_target"] = "login"
        st.rerun()
