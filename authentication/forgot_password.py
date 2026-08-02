"""
authentication/forgot_password.py

Purpose: Streamlit page where a user requests a password reset link by
email. Always shows the same generic confirmation message whether or
not the email exists in the system, to avoid leaking which emails are
registered (a standard account-enumeration defense).
"""

import streamlit as st

from custom_exceptions import ValidationError
from logging_config import logger

from authentication.auth_service import AuthService
from authentication.middleware import guest_only

GENERIC_CONFIRMATION = (
    "If an account exists with that email address, a password reset link has been sent."
)


@guest_only
def render() -> None:
    """Render the Forgot Password page. Entry point called from app.py's router."""
    st.markdown("### Forgot your password?")
    st.caption("Enter your email address and we'll send you a link to reset your password.")

    with st.form("forgot_password_form"):
        email = st.text_input("Email", placeholder="jane@example.com")
        submitted = st.form_submit_button("Send Reset Link", use_container_width=True)

    if submitted:
        try:
            raw_token = AuthService.request_password_reset(email)
            st.success(GENERIC_CONFIRMATION)

            if raw_token is not None:
                # NOTE: Phase 1/2 has no email-sending service wired up yet.
                # In production this token would be emailed, never shown on
                # screen. It is surfaced here only so the reset flow is
                # testable end-to-end without an SMTP integration.
                reset_url = f"?page=reset_password&token={raw_token}"
                st.info(f"Development mode: reset link -> `{reset_url}`")
        except ValidationError as exc:
            st.warning(exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error during forgot-password request: {exc}")
            st.error("Something went wrong. Please try again.")

    st.markdown("---")
    if st.button("Back to Login", use_container_width=True):
        st.session_state["nav_target"] = "login"
        st.rerun()
