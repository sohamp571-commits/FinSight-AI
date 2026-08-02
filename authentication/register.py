"""
authentication/register.py

Purpose: Streamlit page for new user registration. Collects full name,
email, username, and password (with confirmation), performs live
validation feedback, and creates the account via AuthService.
"""

import streamlit as st

from custom_exceptions import DuplicateRecordError, ValidationError
from logging_config import logger

from authentication.auth_service import AuthService
from authentication.middleware import guest_only


@guest_only
def render() -> None:
    """Render the Registration page. Entry point called from app.py's router."""
    st.markdown("### Create your FinSight AI account")
    st.caption("Track your portfolio, get AI predictions, and stay ahead of the market.")

    with st.form("register_form", clear_on_submit=False):
        full_name = st.text_input("Full Name", placeholder="Jane Doe")
        email = st.text_input("Email", placeholder="jane@example.com")
        username = st.text_input("Username", placeholder="jane_doe")
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("Password", type="password", placeholder="At least 8 characters")
        with col2:
            confirm_password = st.text_input("Confirm Password", type="password")

        st.caption("Password must be at least 8 characters and include a letter and a number.")
        agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        if not agree_terms:
            st.warning("Please accept the Terms of Service to continue.")
            return
        try:
            new_user = AuthService.register_user(full_name, email, username, password, confirm_password)
            st.success(f"Account created for {new_user.full_name}! You can now log in.")
            st.session_state["nav_target"] = "login"
            st.rerun()
        except DuplicateRecordError as exc:
            st.error(exc.message)
        except ValidationError as exc:
            st.warning(exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error during registration: {exc}")
            st.error("Something went wrong while creating your account. Please try again.")

    st.markdown("---")
    if st.button("Already have an account? Log in", use_container_width=True):
        st.session_state["nav_target"] = "login"
        st.rerun()
