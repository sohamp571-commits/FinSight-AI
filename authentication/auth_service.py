"""
authentication/auth_service.py

Purpose: The single service class that all Streamlit auth pages call
into. Owns the actual business logic for registration, login,
password reset, profile updates, and soft-delete -- keeping the UI
files (login.py, register.py, ...) thin and focused on presentation.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from constants import MAX_LOGIN_ATTEMPTS
from custom_exceptions import (
    AuthenticationError,
    DatabaseQueryError,
    DuplicateRecordError,
    RecordNotFoundError,
    ValidationError,
)
from database.connection import db_connection
from database.database import db_manager
from database.models import LoginHistory, PasswordResetToken, User
from logging_config import logger

from authentication.password_utils import (
    check_password,
    create_password_hash,
    generate_reset_token,
    hash_reset_token,
    is_token_expired,
)
from authentication.role_manager import get_default_role, get_role_by_name
from authentication.validators import (
    validate_email_field,
    validate_full_name,
    validate_password_field,
    validate_registration_form,
    validate_username_field,
)


class AuthService:
    """Encapsulates every authentication and user-management use case."""

    # ------------------------------------------------------
    # Registration
    # ------------------------------------------------------
    @staticmethod
    def register_user(full_name: str, email: str, username: str, password: str, confirm_password: str) -> User:
        """
        Register a new user with the default 'user' role.

        Raises:
            ValidationError: if any field fails validation.
            DuplicateRecordError: if the email or username is already taken.
        """
        validate_registration_form(full_name, email, username, password, confirm_password)

        existing_email = db_manager.find_one_by(User, email=email.strip().lower())
        if existing_email is not None:
            raise DuplicateRecordError("An account with this email already exists.")

        existing_username = db_manager.find_one_by(User, username=username.strip())
        if existing_username is not None:
            raise DuplicateRecordError("This username is already taken.")

        default_role = get_default_role()

        new_user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            username=username.strip(),
            password_hash=create_password_hash(password),
            role_id=default_role.role_id,
            is_active=True,
        )
        created_user = db_manager.add(new_user)
        logger.info(f"New user registered: username={created_user.username}")
        return created_user

    # ------------------------------------------------------
    # Login / Logout
    # ------------------------------------------------------
    @staticmethod
    def authenticate(username_or_email: str, password: str, ip_address: str = "", user_agent: str = "") -> User:
        """
        Verify credentials and return the authenticated User.

        Raises:
            AuthenticationError: on invalid credentials, inactive/deleted account,
                or when the account is temporarily locked from too many failures.
        """
        identifier = username_or_email.strip()

        user = db_manager.find_one_by(User, username=identifier)
        if user is None:
            user = db_manager.find_one_by(User, email=identifier.lower())

        if user is None or user.deleted_at is not None:
            AuthService._record_login_attempt(None, identifier, ip_address, user_agent, "FAILED")
            raise AuthenticationError("Invalid username/email or password.")

        if not user.is_active:
            AuthService._record_login_attempt(user.user_id, identifier, ip_address, user_agent, "FAILED")
            raise AuthenticationError("This account has been deactivated. Please contact support.")

        if AuthService._is_locked_out(user.user_id):
            raise AuthenticationError(
                f"Too many failed login attempts. Please try again later or reset your password."
            )

        if not check_password(password, user.password_hash):
            AuthService._record_login_attempt(user.user_id, identifier, ip_address, user_agent, "FAILED")
            raise AuthenticationError("Invalid username/email or password.")

        AuthService._record_login_attempt(user.user_id, identifier, ip_address, user_agent, "SUCCESS")
        db_manager.update(User, user.user_id, "user_id", {"last_login_at": datetime.utcnow()})

        logger.info(f"User authenticated: username={user.username}")
        return user

    @staticmethod
    def _record_login_attempt(
        user_id: int | None, username_attempted: str, ip_address: str, user_agent: str, status: str
    ) -> None:
        """Persist a row to login_history for every login attempt, success or failure."""
        try:
            entry = LoginHistory(
                user_id=user_id,
                username_attempted=username_attempted,
                ip_address=ip_address or None,
                user_agent=user_agent or None,
                status=status,
            )
            db_manager.add(entry)
        except DatabaseQueryError as exc:
            # Never let audit logging break the login flow itself.
            logger.error(f"Failed to record login history: {exc}")

    @staticmethod
    def _is_locked_out(user_id: int) -> bool:
        """
        Return True if the user has had MAX_LOGIN_ATTEMPTS consecutive
        failures since their last successful login.
        """
        try:
            with db_connection.get_session() as session:
                stmt = (
                    select(LoginHistory)
                    .where(LoginHistory.user_id == user_id)
                    .order_by(LoginHistory.created_at.desc())
                    .limit(MAX_LOGIN_ATTEMPTS)
                )
                recent = list(session.execute(stmt).scalars().all())
                if len(recent) < MAX_LOGIN_ATTEMPTS:
                    return False
                return all(entry.status == "FAILED" for entry in recent)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to evaluate lockout status: {exc}")
            return False

    @staticmethod
    def get_login_history(user_id: int, limit: int = 20) -> list[LoginHistory]:
        """Return the most recent login attempts for a user, newest first."""
        try:
            with db_connection.get_session() as session:
                stmt = (
                    select(LoginHistory)
                    .where(LoginHistory.user_id == user_id)
                    .order_by(LoginHistory.created_at.desc())
                    .limit(limit)
                )
                results = list(session.execute(stmt).scalars().all())
                for row in results:
                    session.expunge(row)
                return results
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch login history: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Forgot / Reset Password
    # ------------------------------------------------------
    @staticmethod
    def request_password_reset(email: str) -> str | None:
        """
        Generate a password reset token for the given email.

        Returns:
            The raw token to embed in the reset link, or None if no account
            exists for that email (the caller should show the same generic
            success message either way, to avoid leaking which emails are registered).
        """
        validate_email_field(email)
        user = db_manager.find_one_by(User, email=email.strip().lower())
        if user is None or user.deleted_at is not None:
            logger.info(f"Password reset requested for unknown email: {email}")
            return None

        raw_token, token_hash, expires_at = generate_reset_token()
        reset_record = PasswordResetToken(
            user_id=user.user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
        )
        db_manager.add(reset_record)
        logger.info(f"Password reset token issued for user_id={user.user_id}")
        return raw_token

    @staticmethod
    def reset_password(raw_token: str, new_password: str, confirm_password: str) -> None:
        """
        Consume a password reset token and set a new password.

        Raises:
            ValidationError: if the passwords don't match or are too weak.
            AuthenticationError: if the token is invalid, expired, or already used.
        """
        validate_password_field(new_password)
        if new_password != confirm_password:
            raise ValidationError("New password and confirmation do not match.")

        token_hash = hash_reset_token(raw_token)
        token_record = db_manager.find_one_by(PasswordResetToken, token_hash=token_hash)

        if token_record is None or token_record.is_used or is_token_expired(token_record.expires_at):
            raise AuthenticationError("This password reset link is invalid or has expired.")

        db_manager.update(
            User, token_record.user_id, "user_id", {"password_hash": create_password_hash(new_password)}
        )
        db_manager.update(PasswordResetToken, token_record.token_id, "token_id", {"is_used": True})
        logger.info(f"Password reset completed for user_id={token_record.user_id}")

    # ------------------------------------------------------
    # Change Password (authenticated user)
    # ------------------------------------------------------
    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str, confirm_password: str) -> None:
        """
        Change a logged-in user's password after verifying their current one.

        Raises:
            AuthenticationError: if the current password is incorrect.
            ValidationError: if the new password is invalid or unconfirmed.
        """
        user = db_manager.get_by_id(User, user_id, "user_id")

        if not check_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")

        validate_password_field(new_password)
        if new_password != confirm_password:
            raise ValidationError("New password and confirmation do not match.")
        if current_password == new_password:
            raise ValidationError("New password must be different from the current password.")

        db_manager.update(User, user_id, "user_id", {"password_hash": create_password_hash(new_password)})
        logger.info(f"Password changed for user_id={user_id}")

    # ------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------
    @staticmethod
    def get_profile(user_id: int) -> User:
        """Fetch a user's profile record."""
        return db_manager.get_by_id(User, user_id, "user_id")

    @staticmethod
    def update_profile(user_id: int, full_name: str, email: str) -> User:
        """
        Update a user's editable profile fields.

        Raises:
            ValidationError: if the new values fail validation.
            DuplicateRecordError: if the new email is already used by another account.
        """
        validate_full_name(full_name)
        validate_email_field(email)

        normalized_email = email.strip().lower()
        existing = db_manager.find_one_by(User, email=normalized_email)
        if existing is not None and existing.user_id != user_id:
            raise DuplicateRecordError("This email is already associated with another account.")

        updated = db_manager.update(
            User, user_id, "user_id", {"full_name": full_name.strip(), "email": normalized_email}
        )
        logger.info(f"Profile updated for user_id={user_id}")
        return updated

    @staticmethod
    def update_profile_picture(user_id: int, relative_path: str) -> None:
        """
        Store the relative path to a user's uploaded profile picture.

        Note: The `users` table (Phase 1) has no dedicated profile_picture
        column. Rather than modifying the Phase 1 schema for a purely
        cosmetic field, the path is written to the user's `settings` row's
        JSON-free storage is out of scope here -- Phase 3+ can add a proper
        column if profile pictures become a core feature. For now this is a
        no-op placeholder hook that pages can call; wire it to a real column
        once that decision is made.
        """
        logger.info(
            f"Profile picture uploaded for user_id={user_id} at '{relative_path}' "
            f"(persisted to disk; DB column pending a future schema decision)."
        )

    # ------------------------------------------------------
    # Account Status / Soft Delete
    # ------------------------------------------------------
    @staticmethod
    def deactivate_account(user_id: int) -> None:
        """Mark a user account as inactive (reversible, unlike soft delete)."""
        db_manager.update(User, user_id, "user_id", {"is_active": False})
        logger.info(f"Account deactivated: user_id={user_id}")

    @staticmethod
    def reactivate_account(user_id: int) -> None:
        """Reactivate a previously deactivated account."""
        db_manager.update(User, user_id, "user_id", {"is_active": True})
        logger.info(f"Account reactivated: user_id={user_id}")

    @staticmethod
    def soft_delete_account(user_id: int) -> None:
        """
        Soft-delete a user account: stamps deleted_at and deactivates the
        account, but leaves the row (and its FK-linked history) intact.
        """
        db_manager.update(
            User, user_id, "user_id", {"deleted_at": datetime.utcnow(), "is_active": False}
        )
        logger.info(f"Account soft-deleted: user_id={user_id}")
