"""
app.py

Main Streamlit entry point for FinSight AI.

Responsibilities:
    - Configure the Streamlit page (title, icon, layout)
    - Verify the database is reachable before rendering anything
    - Initialize default session-state values
    - Load the current user's theme preference
    - Route between pages based on authentication state and
      st.session_state["nav_target"]
    - Render the sidebar/navigation for authenticated users
    - Wrap the whole render cycle in structured error handling + logging

Run with:  streamlit run app.py
"""

import streamlit as st

from config import config
from constants import APP_ICON, APP_TAGLINE, APP_TITLE
from custom_exceptions import FinSightBaseException
from database.connection import db_connection
from logging_config import logger

from authentication import change_password, forgot_password, login, logout, profile, register, reset_password
from authentication.session_manager import (
    get_current_full_name,
    get_current_role,
    get_current_user_id,
    get_current_username,
    is_authenticated,
)

# Phase 4-11 feature modules, wired into navigation for the first time in Phase 12.
from ai_assistant import assistant_dashboard
from analytics import technical_analysis
from dashboard import home_dashboard, settings_view, watchlist_view
from dashboard.dashboard import render as render_market_dashboard
from machine_learning import prediction_dashboard
from market_intelligence import news_dashboard
from portfolio import portfolio_dashboard
from reports import report_dashboard
from stock_search import stock_search

# ==========================================================
# Streamlit Page Configuration (must run once, before any other st.* call)
# ==========================================================
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================
# Page Registry
# --------------------------------------------------------
# Maps a page key (used by st.session_state["nav_target"]) to the
# module-level render() function that draws it. Later phases append
# to this dict (e.g. "dashboard": dashboard.render) without touching
# the routing logic below.
# ==========================================================
GUEST_PAGES = {
    "login": login.render,
    "register": register.render,
    "forgot_password": forgot_password.render,
    "reset_password": reset_password.render,
}

AUTHENTICATED_PAGES = {
    "dashboard": home_dashboard.render,
    "market_dashboard": render_market_dashboard,
    "stock_search": stock_search.render,
    "portfolio": portfolio_dashboard.render,
    "watchlist": watchlist_view.render,
    "technical_analysis": technical_analysis.render,
    "ai_prediction": prediction_dashboard.render,
    "ai_assistant": assistant_dashboard.render,
    "news": news_dashboard.render,
    "reports": report_dashboard.render,
    "settings": settings_view.render,
    "profile": profile.render,
    "change_password": change_password.render,
    "logout": logout.render,
}


def _init_session_defaults() -> None:
    """Ensure every session-state key the app depends on has a sane default."""
    st.session_state.setdefault("nav_target", "login")
    st.session_state.setdefault("theme", "light")
    st.session_state.setdefault("db_verified", False)


def _verify_database() -> bool:
    """
    Ping the database once per session and cache the result, so every
    rerun doesn't re-open a connection just to check connectivity.
    """
    if st.session_state.get("db_verified"):
        return True

    connected = db_connection.test_connection()
    st.session_state["db_verified"] = connected
    if not connected:
        logger.error("Database connectivity check failed at application startup.")
    return connected


def _load_theme() -> None:
    """
    Apply the current user's saved theme preference (if logged in) or
    the session default, via a light CSS injection. Streamlit's native
    theme is set in .streamlit/config.toml; this layer adds
    FinSight-specific accent styling on top of light/dark mode.
    """
    if is_authenticated():
        try:
            from database.settings_service import settings_service

            user_id = st.session_state.get("auth_user_id")
            if user_id is not None:
                settings = settings_service.get_or_create(user_id)
                st.session_state["theme"] = settings.theme
        except FinSightBaseException as exc:
            logger.warning(f"Could not load user theme preference, using default: {exc}")

    theme = st.session_state.get("theme", "light")
    accent = "#4F8BF9"
    background = "#0E1117" if theme == "dark" else "#FFFFFF"
    text_color = "#FAFAFA" if theme == "dark" else "#111111"

    st.markdown(
        f"""
        <style>
        :root {{
            --finsight-accent: {accent};
        }}
        .stApp {{
            background-color: {background};
            color: {text_color};
        }}

        /* ---- Phase 12: sidebar branding & identity card ---- */
        .finsight-sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .finsight-sidebar-icon {{ font-size: 1.4rem; }}
        .finsight-sidebar-title {{
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: -0.01em;
        }}
        .finsight-sidebar-tagline {{
            font-size: 0.72rem;
            opacity: 0.6;
            margin-top: 0.1rem;
        }}
        .finsight-sidebar-card {{
          background: rgba(79, 139, 249, 0.06);
          border: 1px solid rgba(148, 163, 184, 0.15);
          border-radius: 14px;
          padding: 0.85rem 1rem;
        }}
        .finsight-avatar-placeholder {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4F8BF9, #22D3EE);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }}
        .finsight-role-badge, .finsight-status-badge {{
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            margin-top: 0.5rem;
            margin-right: 0.35rem;
        }}
        .finsight-role-badge {{
            background: rgba(79, 139, 249, 0.15);
            color: #4F8BF9;
        }}
        .finsight-status-badge {{
            background: rgba(34, 197, 94, 0.15);
            color: #22C55E;
        }}

        /* ---- Phase 12: global button polish (hover lift + smooth transition) ---- */
        .stButton > button {{
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            border-radius: 10px;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(79, 139, 249, 0.18);
        }}

        /* ---- Phase 12: consistent rounded, shadowed cards for st.metric blocks ---- */
        [data-testid="stMetric"] {{
            background: rgba(148, 163, 184, 0.06);
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            border-color: rgba(79, 139, 249, 0.35);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard", "🏠", "Dashboard"),
    ("stock_search", "🔍", "Stock Search"),
    ("portfolio", "💼", "Portfolio"),
    ("watchlist", "⭐", "Watchlist"),
    ("technical_analysis", "📉", "Technical Analysis"),
    ("ai_prediction", "🤖", "AI Prediction"),
    ("ai_assistant", "💬", "AI Assistant"),
    ("news", "📰", "News"),
    ("reports", "📑", "Reports"),
    ("market_dashboard", "🌐", "Market Dashboard"),
]


def _find_profile_picture(user_id: int):
    """
    Look up an existing profile picture on disk for the sidebar avatar.
    Reuses `authentication.profile.PROFILE_PICTURES_DIR` (a public
    module-level constant) rather than reimplementing the storage
    convention, and never touches profile.py's own logic.
    """
    for extension in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = profile.PROFILE_PICTURES_DIR / f"user_{user_id}{extension}"
        if candidate.exists():
            return candidate
    return None


def _render_sidebar() -> None:
    """Render the redesigned sidebar for authenticated users: identity, navigation, logout."""
    with st.sidebar:
        st.markdown(
            f"""
            <div class="finsight-sidebar-brand">
                <span class="finsight-sidebar-icon">{APP_ICON}</span>
                <span class="finsight-sidebar-title">{APP_TITLE}</span>
            </div>
            <div class="finsight-sidebar-tagline">{APP_TAGLINE}</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")

        user_id = get_current_user_id()
        full_name = get_current_full_name()
        username = get_current_username()
        role = get_current_role()

        profile_picture = _find_profile_picture(user_id) if user_id is not None else None
        with st.container():
            col_avatar, col_info = st.columns([1, 2])
            with col_avatar:
                if profile_picture is not None:
                    st.image(str(profile_picture), width=56)
                else:
                    st.markdown('<div class="finsight-avatar-placeholder">🧑</div>', unsafe_allow_html=True)
            with col_info:
                st.markdown(f"**{full_name}**")
                st.caption(f"@{username}")
            st.markdown(
                f'<span class="finsight-role-badge">{role.title() if role else "N/A"}</span>'
                f'<span class="finsight-status-badge">🟢 Active</span>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("##### Navigation")

        active_page = st.session_state.get("nav_target", "dashboard")
        for nav_key, icon, label in _NAV_ITEMS:
            is_active = active_page == nav_key
            if st.button(
                f"{icon}  {label}",
                use_container_width=True,
                key=f"nav_{nav_key}",
                type="primary" if is_active else "secondary",
            ):
                st.session_state["nav_target"] = nav_key
                st.rerun()

        st.markdown("---")
        st.markdown("##### Account")
        for nav_key, icon, label in (
            ("settings", "⚙️", "Settings"),
            ("profile", "👤", "Profile"),
            ("change_password", "🔒", "Change Password"),
        ):
            if st.button(f"{icon}  {label}", use_container_width=True, key=f"nav_{nav_key}"):
                st.session_state["nav_target"] = nav_key
                st.rerun()

        st.markdown("---")
        if st.button("🚪  Log Out", use_container_width=True, key="nav_logout"):
            st.session_state["nav_target"] = "logout"
            st.rerun()


def _route() -> None:
    """Decide which page to render based on auth state and nav_target."""
    nav_target = st.session_state.get("nav_target", "login")

    if is_authenticated():
        _render_sidebar()
        if nav_target not in AUTHENTICATED_PAGES:
            # Any stale/guest nav_target while logged in falls back to the dashboard.
            nav_target = "dashboard"
        AUTHENTICATED_PAGES[nav_target]()
    else:
        if nav_target not in GUEST_PAGES:
            nav_target = "login"
        GUEST_PAGES[nav_target]()


def main() -> None:
    """Application entry point."""
    try:
        _init_session_defaults()

        if not _verify_database():
            st.error(
                "⚠️ Unable to connect to the database. Please verify your MySQL "
                "server is running and your `.env` file is configured correctly "
                "(see README.md / docs/deployment.md)."
            )
            st.stop()

        _load_theme()
        _route()

    except FinSightBaseException as exc:
        logger.error(f"Handled application error: {exc}")
        st.error(f"An error occurred: {exc.message}")
    except Exception as exc:  # noqa: BLE001 - last line of defense for the whole app
        logger.exception(f"Unhandled exception in application: {exc}")
        st.error("An unexpected error occurred. Please refresh the page or contact support.")


if __name__ == "__main__":
    logger.info(f"Starting {config.APP_NAME} (env={config.APP_ENV})")
    main()
