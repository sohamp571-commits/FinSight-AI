"""
reports package

Phase 11 — AI Portfolio Report Generator for FinSight AI.

No new database tables: the existing `reports` table (Phase 1 schema,
Phase 3 database.report_service) already covers generated-report
metadata perfectly, and PDF files are written to the existing
constants.REPORTS_DIR_NAME directory (also defined in Phase 1).

Sub-modules:
    report_generator.py   - aggregates report data by calling existing services only
    chart_export.py         - renders static PNG charts (matplotlib) from already-computed data
    pdf_builder.py            - assembles the final PDF (ReportLab): headings, tables, charts, page numbers
    report_dashboard.py        - main controller (entry point: report_dashboard.render)
"""

from reports.report_dashboard import render

__all__ = ["render"]
