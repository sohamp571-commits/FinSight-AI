"""
authentication/validators.py

Purpose: Field-level validation rules specific to the authentication
module (email, username, password strength, full name). Reuses the
generic regex/utility building blocks from utils.py where possible,
and raises custom_exceptions.ValidationError with a user-facing
message on failure so the Streamlit UI can display it directly.
"""

import re

from custom_exceptions import ValidationError
from utils import is_valid_email, is_strong_password

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{4,30}$")
FULL_NAME_REGEX = re.compile(r"^[A-Za-z\s.'-]{2,100}$")


def validate_full_name(full_name: str) -> None:
    """Ensure the full name contains only letters, spaces and basic punctuation."""
    if not full_name or not FULL_NAME_REGEX.match(full_name.strip()):
        raise ValidationError("Full name must be 2-100 characters and contain only letters.")


def validate_email_field(email: str) -> None:
    """Ensure the email is syntactically valid."""
    if not is_valid_email(email):
        raise ValidationError("Please enter a valid email address.")


def validate_username_field(username: str) -> None:
    """
    Ensure the username is 4-30 characters, alphanumeric/underscore only.
    Enforced separately from email since usernames double as the public
    handle shown across the dashboard.
    """
    if not username or not USERNAME_REGEX.match(username.strip()):
        raise ValidationError(
            "Username must be 4-30 characters and contain only letters, numbers, or underscores."
        )


def validate_password_field(password: str) -> None:
    """Ensure the password meets the minimum strength policy (8+ chars, letter + digit)."""
    if not is_strong_password(password):
        raise ValidationError(
            "Password must be at least 8 characters long and include at least one letter and one digit."
        )


def validate_password_confirmation(password: str, confirm_password: str) -> None:
    """Ensure the confirmation field exactly matches the password field."""
    if password != confirm_password:
        raise ValidationError("Password and confirmation password do not match.")


def validate_registration_form(
    full_name: str,
    email: str,
    username: str,
    password: str,
    confirm_password: str,
) -> None:
    """Run every validation rule required for the registration form in one call."""
    validate_full_name(full_name)
    validate_email_field(email)
    validate_username_field(username)
    validate_password_field(password)
    validate_password_confirmation(password, confirm_password)


def validate_profile_picture(file_name: str, file_size_bytes: int) -> None:
    """
    Validate an uploaded profile picture before it is written to disk.

    Args:
        file_name: Original uploaded file name (used to check extension).
        file_size_bytes: Size of the uploaded file in bytes.
    """
    allowed_extensions = (".png", ".jpg", ".jpeg", ".webp")
    max_size_bytes = 2 * 1024 * 1024  # 2 MB

    if not file_name.lower().endswith(allowed_extensions):
        raise ValidationError("Profile picture must be a PNG, JPG, JPEG, or WEBP image.")
    if file_size_bytes > max_size_bytes:
        raise ValidationError("Profile picture must be smaller than 2 MB.")
