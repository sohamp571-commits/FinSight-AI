"""
authentication/profile.py

Purpose: Streamlit page for viewing and editing the logged-in user's
profile: name/email updates, profile picture upload, account status,
and recent login history. This is the "account home" page most users
will see after their dashboard.
"""

from pathlib import Path

import streamlit as st

from config import config
from custom_exceptions import DuplicateRecordError, ValidationError
from helper import format_datetime
from logging_config import logger

from authentication.auth_service import AuthService
from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id, start_session
from authentication.validators import validate_profile_picture

PROFILE_PICTURES_DIR = config.BASE_DIR / "assets" / "images" / "profile_pictures"


@login_required
def render() -> None:
    """Render the Profile page. Entry point called from app.py's router."""
    user_id = get_current_user_id()
    user = AuthService.get_profile(user_id)

    st.markdown("### My Profile")

    col_picture, col_details = st.columns([1, 2])

    with col_picture:
        _render_profile_picture_section(user_id)

    with col_details:
        _render_account_status(user)
        _render_update_profile_form(user)

    st.markdown("---")
    _render_login_history_section(user_id)


def _render_profile_picture_section(user_id: int) -> None:
    """Render the current profile picture (if any) and an uploader for a new one."""
    st.markdown("**Profile Picture**")

    existing_picture = _find_existing_picture(user_id)
    if existing_picture is not None:
        st.image(str(existing_picture), width=160)
    else:
        st.info("No profile picture uploaded yet.")

    uploaded_file = st.file_uploader(
        "Upload new picture", type=["png", "jpg", "jpeg", "webp"], key="profile_picture_uploader"
    )
    if uploaded_file is not None and st.button("Save Picture", use_container_width=True):
        try:
            file_bytes = uploaded_file.getvalue()
            validate_profile_picture(uploaded_file.name, len(file_bytes))

            PROFILE_PICTURES_DIR.mkdir(parents=True, exist_ok=True)
            extension = Path(uploaded_file.name).suffix.lower()
            destination = PROFILE_PICTURES_DIR / f"user_{user_id}{extension}"
            destination.write_bytes(file_bytes)

            AuthService.update_profile_picture(user_id, str(destination.relative_to(config.BASE_DIR)))
            st.success("Profile picture updated.")
            st.rerun()
        except ValidationError as exc:
            st.warning(exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error uploading profile picture: {exc}")
            st.error("Something went wrong while uploading your picture. Please try again.")


def _find_existing_picture(user_id: int) -> Path | None:
    """Look for a previously uploaded profile picture on disk for this user."""
    if not PROFILE_PICTURES_DIR.exists():
        return None
    for extension in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = PROFILE_PICTURES_DIR / f"user_{user_id}{extension}"
        if candidate.exists():
            return candidate
    return None


def _render_account_status(user) -> None:
    """Display read-only account metadata: role, status, timestamps."""
    status_label = "🟢 Active" if user.is_active else "🔴 Inactive"
    st.markdown(f"**Status:** {status_label}")
    st.markdown(f"**Role:** {user.role.role_name.title()}")
    st.markdown(f"**Member since:** {format_datetime(user.created_at)}")
    st.markdown(
        f"**Last login:** {format_datetime(user.last_login_at) if user.last_login_at else 'This is your first login'}"
    )


def _render_update_profile_form(user) -> None:
    """Render the editable full name / email form."""
    st.markdown("**Update Details**")
    with st.form("update_profile_form"):
        full_name = st.text_input("Full Name", value=user.full_name)
        email = st.text_input("Email", value=user.email)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Username", value=user.username, disabled=True, help="Usernames cannot be changed.")
        submitted = st.form_submit_button("Save Changes", use_container_width=True)

    if submitted:
        try:
            updated_user = AuthService.update_profile(user.user_id, full_name, email)
            start_session(
                user_id=updated_user.user_id,
                username=updated_user.username,
                full_name=updated_user.full_name,
                role_name=updated_user.role.role_name,
            )
            st.success("Profile updated successfully.")
            st.rerun()
        except DuplicateRecordError as exc:
            st.error(exc.message)
        except ValidationError as exc:
            st.warning(exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error updating profile: {exc}")
            st.error("Something went wrong while updating your profile. Please try again.")


def _render_login_history_section(user_id: int) -> None:
    """Display the user's most recent login attempts."""
    st.markdown("**Recent Login Activity**")
    try:
        history = AuthService.get_login_history(user_id, limit=10)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load login history: {exc}")
        st.info("Login history is currently unavailable.")
        return

    if not history:
        st.info("No login activity recorded yet.")
        return

    for entry in history:
        icon = "✅" if entry.status == "SUCCESS" else "❌"
        ip_label = entry.ip_address or "unknown IP"
        st.write(f"{icon} {format_datetime(entry.created_at)} — {entry.status.title()} — {ip_label}")
