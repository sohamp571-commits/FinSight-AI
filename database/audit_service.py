"""
database/audit_service.py

Purpose: Data-layer service for the `audit_logs` table -- a
write-heavy, append-mostly log of security/business-relevant actions
(login, password change, profile update, admin actions, etc.), used
for compliance and troubleshooting. Distinct from loguru's
application logs (logging_config.py): audit_logs is structured,
queryable, and tied to specific user/entity records.
"""

from typing import Any

from custom_exceptions import DatabaseQueryError
from database.base_service import BaseService
from database.connection import db_connection
from database.models import AuditLog
from logging_config import logger


class AuditService(BaseService[AuditLog]):
    """Write and query operations for the `audit_logs` table."""

    model = AuditLog
    pk_column = "audit_log_id"

    def log_action(
        self,
        action: str,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        ip_address: str | None = None,
        details: str | None = None,
    ) -> AuditLog | None:
        """
        Record an audit entry. Failures here are logged but never
        raised -- an audit-logging bug must not be allowed to break
        the primary operation it's describing (mirrors the same
        philosophy as AuthService._record_login_attempt).
        """
        try:
            return self.create(
                AuditLog(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=ip_address,
                    details=details,
                )
            )
        except DatabaseQueryError as exc:
            logger.error(f"Failed to write audit log entry (action='{action}'): {exc}")
            return None

    def get_logs_for_user(self, user_id: int, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """List every audit entry associated with a specific user, newest first."""
        return self.list(
            filters={"user_id": user_id}, sort_by="created_at", sort_direction="desc", page=page, page_size=page_size
        )

    def get_logs_for_action(self, action: str, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """List every audit entry for a specific action type, newest first (e.g. admin review)."""
        return self.list(
            filters={"action": action}, sort_by="created_at", sort_direction="desc", page=page, page_size=page_size
        )

    def search_logs(self, search_term: str, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """Search audit entries by action name or free-text details."""
        return self.list(
            search_term=search_term,
            search_columns=["action", "details"],
            sort_by="created_at",
            sort_direction="desc",
            page=page,
            page_size=page_size,
        )


audit_service = AuditService()
