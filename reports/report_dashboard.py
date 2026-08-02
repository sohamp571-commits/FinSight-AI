"""
reports/report_dashboard.py

Purpose: The main entry point for the AI Portfolio Report Generator.
Shows an in-app preview of what the report will contain, then a
"Generate PDF Report" button that calls report_generator.py +
pdf_builder.py and offers the result via st.download_button. Reuses
the existing `reports` table (Phase 3 database.report_service) to log
each generated report -- no new table, exactly as instructed.
"""

from pathlib import Path

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_full_name, get_current_user_id
from config import config
from constants import REPORTS_DIR_NAME, ReportType
from custom_exceptions import FinSightBaseException
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from database.audit_service import audit_service
from database.report_service import report_service
from helper import format_currency, format_datetime, format_percentage
from logging_config import logger

from reports.report_generator import generate_report_data
from reports.pdf_builder import build_portfolio_report_pdf

REPORTS_OUTPUT_DIR: Path = config.BASE_DIR / REPORTS_DIR_NAME
REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _render_preview(user_id: int) -> None:
    """Render a lightweight in-app preview of the report's headline numbers before generating the PDF."""
    from portfolio.portfolio_calculator import compute_portfolio_overview
    from portfolio.risk_analysis import compute_risk_report

    overview = compute_portfolio_overview(user_id)
    risk = compute_risk_report(user_id)

    render_section_header("Report Preview", icon="👁️")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Investment", format_currency(overview.total_investment, "₹"))
    with col2:
        st.metric("Current Value", format_currency(overview.current_value, "₹"))
    with col3:
        st.metric("Total P&L", format_percentage(overview.total_profit_loss_pct))
    with col4:
        st.metric("Risk Score", f"{risk.risk_score:.0f}/100")

    st.caption(
        "The full PDF report additionally includes: allocation & sector charts, portfolio growth chart, "
        "top winners/losers, performance metrics (Sharpe, Beta, Volatility, Max Drawdown), dividend summary, "
        "a recommendation summary, and an AI Assistant summary."
    )


def _render_past_reports(user_id: int) -> None:
    """List previously generated reports (reused from the existing `reports` table)."""
    render_section_header("Past Reports", icon="🗂️")
    past_reports = report_service.get_user_reports(user_id, report_type=ReportType.PORTFOLIO_SUMMARY.value, page_size=10)["items"]
    if not past_reports:
        st.caption("No reports generated yet.")
        return

    for report in past_reports:
        file_path = Path(report.file_path)
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"📄 {file_path.name}  •  {format_datetime(report.generated_at)}")
        with col2:
            if file_path.exists():
                st.download_button(
                    "Download", data=file_path.read_bytes(), file_name=file_path.name,
                    mime="application/pdf", key=f"download_past_{report.report_id}", use_container_width=True,
                )
            else:
                st.caption("File no longer available")


@login_required
def render() -> None:
    """Render the full AI Portfolio Report Generator page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()
        full_name = get_current_full_name() or "Investor"

        st.title("📑 Portfolio Report Generator")
        st.caption("Export a complete, professional PDF investment report combining every FinSight AI module.")
        render_divider()

        _render_preview(user_id)
        render_divider()

        if st.button("📥 Generate PDF Report", type="primary", use_container_width=True):
            with st.spinner("Gathering portfolio data and building your report..."):
                report_data = generate_report_data(user_id, full_name)
                pdf_bytes = build_portfolio_report_pdf(report_data)

                filename = f"portfolio_report_{user_id}_{report_data.generated_at.strftime('%Y%m%d_%H%M%S')}.pdf"
                file_path = REPORTS_OUTPUT_DIR / filename
                file_path.write_bytes(pdf_bytes)

                report_service.log_report(
                    user_id=user_id, report_type=ReportType.PORTFOLIO_SUMMARY.value, file_path=str(file_path)
                )
                audit_service.log_action(action="PORTFOLIO_REPORT_GENERATED", user_id=user_id, entity_type="report")

            st.success("Your report is ready.")
            st.download_button(
                "⬇️ Download Report", data=pdf_bytes, file_name=filename,
                mime="application/pdf", use_container_width=True,
            )

        render_divider()
        _render_past_reports(user_id)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in report dashboard: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in report dashboard: {exc}")
        st.error("An unexpected error occurred while generating the report. Please try again.")
