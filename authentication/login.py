"""
authentication/login.py

Purpose: Streamlit page for user login. Presents a username/email +
password form with a "Remember Me" checkbox, validates credentials via
AuthService, and starts a session on success.
"""

from datetime import datetime

import streamlit as st

from custom_exceptions import AuthenticationError, ValidationError
from logging_config import logger

from authentication.auth_service import AuthService
from authentication.middleware import guest_only
from authentication.session_manager import start_session


def _apply_page_style() -> None:
    """
    Inject the login page's visual styling: a gradient page background,
    a real glassmorphism card (targeting the auto-generated
    `.st-key-login_card` class from `st.container(key="login_card")`
    -- NOT the broken manual `st.markdown('<div>...')` wrapper this
    previously used, which rendered as an empty floating box because
    Streamlit doesn't nest later widgets inside a div opened by an
    earlier, separate `st.markdown()` call), and animated button
    hover effects.
    """
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at 15% 15%, rgba(79,139,249,0.16), transparent 45%),
                        radial-gradient(circle at 85% 85%, rgba(34,197,94,0.10), transparent 45%),
                        linear-gradient(160deg, #0B1120 0%, #0E1117 55%, #10182B 100%);
        }

        .finsight-brand {
            text-align: center;
            margin: 2.5rem auto 1.5rem auto;
        }
        .finsight-brand-icon {
            font-size: 2.75rem;
            line-height: 1;
        }
        .finsight-brand-title {
            font-size: 1.9rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #4F8BF9, #22D3EE);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 0.35rem;
        }
        .finsight-brand-tagline {
            font-size: 0.88rem;
            color: #94A3B8;
            margin-top: 0.15rem;
        }

        /* Glassmorphism card -- the REAL container Streamlit guarantees
           wraps everything rendered inside `with st.container()`. */
        .st-key-login_card {
            max-width: 440px;
            margin: 0 auto;
            padding: 2.25rem 2.25rem 1.5rem 2.25rem;
            border-radius: 20px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: rgba(30, 41, 59, 0.45);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
        }

        .auth-title {
            font-size: 1.45rem;
            font-weight: 700;
            color: #F1F5F9;
            margin-bottom: 0.15rem;
        }
        .auth-subtitle {
            font-size: 0.88rem;
            color: #94A3B8;
            margin-bottom: 1.4rem;
        }

        /* Animated, hover-responsive buttons across the whole page */
        .stButton > button, [data-testid="stFormSubmitButton"] button {
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
            border-radius: 10px;
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(79, 139, 249, 0.25);
            border-color: rgba(79, 139, 249, 0.6);
        }
        [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(90deg, #4F8BF9, #3B82F6);
            color: white;
            font-weight: 600;
            border: none;
        }

        .finsight-footer {
            text-align: center;
            margin-top: 2.5rem;
            padding-bottom: 1.5rem;
            font-size: 0.78rem;
            color: #64748B;
        }

        @media (max-width: 480px) {
            .st-key-login_card { padding: 1.5rem 1.25rem 1rem 1.25rem; border-radius: 14px; }
        }
             /* Labels */
             .stTextInput label,
            .stCheckbox label,
            .stSelectbox label,
            .stTextArea label,
            .stNumberInput label,
            [data-testid="stWidgetLabel"] p {
            color: #FFFFFF !important;
             font-weight: 600;
        }

           /* Checkbox text */
            [data-testid="stCheckbox"] label p {
            color: #FFFFFF !important;
        }

            /* Input text */
            .stTextInput input,
            input[type="password"] {
            color: #000000 !important;
            background-color: #FFFFFF !important;
            caret-color: #000000 !important;
        }
         /* Selected text */
          .stTextInput input::selection {
             background: #4F8BF9;
             color: #FFFFFF;
          }

            /* Password eye icon */
            [data-testid="stTextInput"] svg {
            color: #000000 !important;
          }
               /* Placeholder */
                .stTextInput input::placeholder {
                 color: #94A3B8 !important;
                }
          </style>
        """,
        unsafe_allow_html=True,
    )


def _render_branding() -> None:
    """
    Render the professional FinSight AI branding section above the
    login card -- this is real, populated content (logo + title +
    tagline), replacing the empty rounded rectangle that used to
    render here.
    """
    st.markdown(
        """
        <div class="finsight-brand">
            <div class="finsight-brand-icon">📈</div>
            <div class="finsight-brand-title">FinSight AI</div>
            <div class="finsight-brand-tagline">AI-Powered Stock Market Intelligence & Portfolio Analytics</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    """Render a small branded footer beneath the login card."""
    st.markdown(
        f'<div class="finsight-footer">© {datetime.utcnow().year} FinSight AI • '
        f"Built for smarter investing, not financial advice.</div>",
        unsafe_allow_html=True,
    )


@guest_only
def render() -> None:
    """Render the Login page. Entry point called from app.py's router."""
    _apply_page_style()
    _render_branding()

    with st.container():
        st.markdown('<div class="auth-title">Welcome back 👋</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Log in to your FinSight AI account</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            identifier = st.text_input("Username or Email", placeholder="jane.doe or jane@example.com")
            # `type="password"` already renders Streamlit's native show/hide
            # (eye icon) visibility toggle -- no custom toggle needed.
            password = st.text_input("Password", type="password", placeholder="••••••••")
            remember_me = st.checkbox("Remember me for 30 days", value=False)
            submitted = st.form_submit_button("Log In", use_container_width=True)

        if submitted:
            try:
                user = AuthService.authenticate(identifier, password)
                start_session(
                    user_id=user.user_id,
                    username=user.username,
                    full_name=user.full_name,
                    role_name=user.role.role_name,
                    remember_me=remember_me,
                )
                st.success(f"Welcome back, {user.full_name}!")
                st.rerun()
            except AuthenticationError as exc:
                st.error(exc.message)
            except ValidationError as exc:
                st.warning(exc.message)
            except Exception as exc:  # noqa: BLE001 - surface unexpected errors safely
                logger.error(f"Unexpected error during login: {exc}")
                st.error("Something went wrong while logging in. Please try again.")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create an account", use_container_width=True):
                st.session_state["nav_target"] = "register"
                st.rerun()
        with col2:
            if st.button("Forgot password?", use_container_width=True):
                st.session_state["nav_target"] = "forgot_password"
                st.rerun()

    _render_footer()
