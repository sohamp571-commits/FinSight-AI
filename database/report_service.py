"""
database/report_service.py

Purpose: Data-layer service for the `reports` table -- tracks
generated PDF/Excel report files (portfolio summaries, prediction
summaries, transaction history) so users can re-download past reports
instead of regenerating them. Actual PDF/Excel generation happens in
the `reports/` feature module in a later phase; this service only
persists the resulting metadata/file path.
"""

from typing import Any

from constants import ReportType
from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import Report
from logging_config import logger


class ReportService(BaseService[Report]):
    """CRUD operations for the `reports` table."""

    model = Report
    pk_column = "report_id"

    def log_report(self, user_id: int, report_type: str, file_path: str) -> Report:
        """Persist a record of a generated report file."""
        valid_types = {item.value for item in ReportType}
        if report_type not in valid_types:
            raise ValidationError(f"report_type must be one of: {', '.join(sorted(valid_types))}")
        if not file_path.strip():
            raise ValidationError("file_path is required.")

        entry = Report(user_id=user_id, report_type=report_type, file_path=file_path.strip())
        created = self.create(entry)
        logger.info(f"Report logged: user_id={user_id}, type={report_type}, path={file_path}")
        return created

    def get_user_reports(
        self, user_id: int, report_type: str | None = None, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        """List a user's generated reports, newest first, optionally filtered by type."""
        filters: dict[str, Any] = {"user_id": user_id}
        if report_type:
            filters["report_type"] = report_type
        return self.list(
            filters=filters, sort_by="generated_at", sort_direction="desc", page=page, page_size=page_size
        )


report_service = ReportService()
