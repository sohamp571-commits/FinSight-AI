"""
dashboard/settings_view.py

Purpose: A Settings page for theme, default currency, and the
notifications master switch. `database.settings_service` (Phase 3)
has provided this functionality since Phase 3 but had no Streamlit
page calling it -- this file is that missing UI, reusing
`get_or_create` / `set_theme` / `set_currency` / `set_notifications`
exactly as written.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from database.settings_service import VALID_CURRENCIES, VALID_THEMES, settings_service
from logging_config import logger


@login_required
def render() -> None:
    """Render the Settings page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("⚙️ Settings")
        render_divider()

        settings = settings_service.get_or_create(user_id)

        render_section_header("Preferences", icon="🎛️")
        with st.form("settings_form"):
            theme = st.selectbox("Theme", VALID_THEMES, index=VALID_THEMES.index(settings.theme))
            currency = st.selectbox(
                "Default Currency", VALID_CURRENCIES, index=VALID_CURRENCIES.index(settings.default_currency)
            )
            notifications_enabled = st.checkbox(
                "Enable notifications", value=settings.notifications_enabled,
                help="Master switch. Granular categories are managed on the News & Notifications page.",
            )
            submitted = st.form_submit_button("Save Settings", use_container_width=True)

        if submitted:
            try:
                if theme != settings.theme:
                    settings_service.set_theme(user_id, theme)
                if currency != settings.default_currency:
                    settings_service.set_currency(user_id, currency)
                if notifications_enabled != settings.notifications_enabled:
                    settings_service.set_notifications(user_id, notifications_enabled)
                st.success("Settings saved. Theme changes apply on your next page load.")
                st.rerun()
            except FinSightBaseException as exc:
                logger.error(f"Failed to save settings for user_id={user_id}: {exc}")
                st.error(exc.message)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in settings view: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in settings view: {exc}")
        st.error("An unexpected error occurred while loading settings. Please try again.")
