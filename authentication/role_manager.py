"""
authentication/role_manager.py

Purpose: Centralizes everything related to the `roles` table and
role-based access control (RBAC) so that permission logic isn't
duplicated across every page. `middleware.py` builds its decorators
on top of the functions defined here.
"""

from constants import UserRole
from custom_exceptions import DatabaseQueryError, RecordNotFoundError
from database.database import db_manager
from database.models import Role
from logging_config import logger

# Roles ordered from least to most privileged. Used for ">=" style checks
# (e.g. "analyst or higher").
_ROLE_HIERARCHY: dict[str, int] = {
    UserRole.USER.value: 1,
    UserRole.ANALYST.value: 2,
    UserRole.ADMIN.value: 3,
}


def get_role_by_name(role_name: str) -> Role:
    """Fetch a Role record by its name, raising if it doesn't exist."""
    role = db_manager.find_one_by(Role, role_name=role_name)
    if role is None:
        raise RecordNotFoundError(f"Role '{role_name}' does not exist.")
    return role


def get_default_role() -> Role:
    """Return the role assigned to newly registered users."""
    try:
        return get_role_by_name(UserRole.USER.value)
    except RecordNotFoundError:
        logger.error("Default 'user' role is missing from the roles table.")
        raise


def role_rank(role_name: str) -> int:
    """Return the numeric privilege rank of a role name (higher = more privileged)."""
    return _ROLE_HIERARCHY.get(role_name, 0)


def has_minimum_role(current_role: str | None, minimum_role: str) -> bool:
    """
    Return True if `current_role` is at least as privileged as `minimum_role`.

    Example:
        has_minimum_role("admin", "analyst")  -> True
        has_minimum_role("user", "analyst")   -> False
    """
    if current_role is None:
        return False
    return role_rank(current_role) >= role_rank(minimum_role)


def is_admin(current_role: str | None) -> bool:
    """Convenience check: is the given role exactly 'admin'?"""
    return current_role == UserRole.ADMIN.value


def list_all_roles() -> list[Role]:
    """Return every role defined in the system, e.g. for an admin-facing dropdown."""
    try:
        return db_manager.get_all(Role, limit=100)
    except DatabaseQueryError:
        logger.error("Failed to list roles.")
        raise
