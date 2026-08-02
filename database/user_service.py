"""
database/user_service.py

Purpose: Data-layer service for the `users` table. Provides generic
CRUD (inherited from BaseService) plus user-specific lookups
(find_by_email, find_by_username), soft-delete/restore, and profile
helpers.

Note: This module is intentionally decoupled from the `authentication`
package (no import of password hashing here) to avoid a circular
dependency -- `authentication.auth_service` sits ABOVE this service
and is responsible for hashing passwords before calling `create_user`.
Anything that just needs "give me / update a user record" (e.g. the
dashboard, admin panel) can use UserService directly instead of going
through the auth layer.
"""

from datetime import datetime
from typing import Any

from custom_exceptions import RecordNotFoundError, ValidationError
from database.base_service import BaseService
from database.models import User
from logging_config import logger
from utils import is_valid_email, validate_required_fields


class UserService(BaseService[User]):
    """CRUD and lookup operations for the `users` table."""

    model = User
    pk_column = "user_id"

    # ------------------------------------------------------
    # Create
    # ------------------------------------------------------
    def create_user(
        self, full_name: str, email: str, username: str, password_hash: str, role_id: int
    ) -> User:
        """
        Create a new user record. `password_hash` must already be
        hashed by the caller (see authentication.password_utils).
        """
        validate_required_fields(
            {"full_name": full_name, "email": email, "username": username, "password_hash": password_hash},
            ["full_name", "email", "username", "password_hash"],
        )
        if not is_valid_email(email):
            raise ValidationError("A valid email address is required.")

        new_user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            username=username.strip(),
            password_hash=password_hash,
            role_id=role_id,
            is_active=True,
        )
        return self.create(new_user)

    # ------------------------------------------------------
    # Read / Lookup
    # ------------------------------------------------------
    def find_by_email(self, email: str) -> User | None:
        """Fetch a user by their (case-normalized) email address."""
        return self.find_one_by(email=email.strip().lower())

    def find_by_username(self, username: str) -> User | None:
        """Fetch a user by their exact username."""
        return self.find_one_by(username=username.strip())

    def get_profile(self, user_id: int) -> User:
        """Fetch a user's full profile record, raising if not found or soft-deleted."""
        user = self.get_by_id(user_id)
        if user.deleted_at is not None:
            raise RecordNotFoundError("This account no longer exists.")
        return user

    def list_active_users(self, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """List users who are active and not soft-deleted, with pagination."""
        return self.list(filters={"is_active": True}, page=page, page_size=page_size, sort_by="created_at")

    def search_users(self, search_term: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """Search users by full name, email, or username."""
        return self.list(
            search_term=search_term,
            search_columns=["full_name", "email", "username"],
            page=page,
            page_size=page_size,
            sort_by="full_name",
        )

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def update_profile(self, user_id: int, full_name: str, email: str) -> User:
        """Update a user's editable profile fields (full name, email)."""
        if not is_valid_email(email):
            raise ValidationError("A valid email address is required.")
        return self.update(user_id, {"full_name": full_name.strip(), "email": email.strip().lower()})

    def update_last_login(self, user_id: int) -> User:
        """Stamp `last_login_at` with the current UTC time."""
        return self.update(user_id, {"last_login_at": datetime.utcnow()})

    # ------------------------------------------------------
    # Delete / Soft Delete / Restore
    # ------------------------------------------------------
    def deactivate(self, user_id: int) -> User:
        """Mark a user as inactive (reversible)."""
        updated = self.update(user_id, {"is_active": False})
        logger.info(f"User deactivated (user_id={user_id}).")
        return updated

    def activate(self, user_id: int) -> User:
        """Mark a user as active."""
        updated = self.update(user_id, {"is_active": True})
        logger.info(f"User activated (user_id={user_id}).")
        return updated

    def soft_delete(self, user_id: int) -> User:
        """Soft-delete a user: stamps deleted_at and deactivates the account."""
        updated = self.update(user_id, {"deleted_at": datetime.utcnow(), "is_active": False})
        logger.info(f"User soft-deleted (user_id={user_id}).")
        return updated

    def restore(self, user_id: int) -> User:
        """Restore a previously soft-deleted user."""
        updated = self.update(user_id, {"deleted_at": None, "is_active": True})
        logger.info(f"User restored (user_id={user_id}).")
        return updated

    def hard_delete(self, user_id: int) -> None:
        """
        Permanently remove a user and (via ON DELETE CASCADE) all of
        their dependent records. Use soft_delete() in normal operation;
        this is reserved for GDPR-style erasure requests.
        """
        self.delete(user_id)
        logger.warning(f"User permanently deleted (user_id={user_id}).")


user_service = UserService()
