"""
reports/pdf_builder.py

Purpose: Assembles the final PDF document using ReportLab (already a
Phase 1 dependency). Takes `ReportData` (report_generator.py) and the
chart PNG bytes (chart_export.py) and lays them out into a professional
report: a cover section with a logo placeholder, section headings,
data tables, embedded charts, and numbered pages via a custom canvas.
No calculation happens here -- this module is presentation-only.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from constants import APP_TITLE
from helper import format_currency, format_datetime, format_percentage
from reports.chart_export import (
    render_allocation_pie_image,
    render_growth_line_image,
    render_risk_gauge_image,
    render_sector_bar_image,
    render_winners_losers_image,
)
from reports.report_generator import ReportData

_ACCENT_COLOR = colors.HexColor("#4F8BF9")
_MUTED_COLOR = colors.HexColor("#64748B")
_POSITIVE_COLOR = colors.HexColor("#22C55E")
_NEGATIVE_COLOR = colors.HexColor("#EF4444")

_styles = getSampleStyleSheet()
_TITLE_STYLE = ParagraphStyle("ReportTitle", parent=_styles["Title"], textColor=_ACCENT_COLOR, fontSize=24, spaceAfter=6)
_SUBTITLE_STYLE = ParagraphStyle("ReportSubtitle", parent=_styles["Normal"], textColor=_MUTED_COLOR, fontSize=10, spaceAfter=18)
_SECTION_STYLE = ParagraphStyle("SectionHeading", parent=_styles["Heading2"], textColor=_ACCENT_COLOR, spaceBefore=18, spaceAfter=8)
_BODY_STYLE = ParagraphStyle("ReportBody", parent=_styles["Normal"], fontSize=10, leading=15)


def _add_page_number(canvas_obj: pdf_canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Draw a footer with the page number and a small branded header line on every page."""
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(_MUTED_COLOR)
    canvas_obj.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc.page}")
    canvas_obj.drawString(2 * cm, A4[1] - 1.2 * cm, f"{APP_TITLE} — Portfolio Report")
    canvas_obj.restoreState()


def _logo_placeholder() -> Table:
    """
    A simple bordered box standing in for a company logo. Real logo
    image support can be added later by swapping this for
    `Image(logo_path, width=..., height=...)` once branding assets exist.
    """
    table = Table([["📈"]], colWidths=[2 * cm], rowHeights=[2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, _ACCENT_COLOR),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 20),
            ]
        )
    )
    return table


def _metric_table(rows: list[tuple[str, str]]) -> Table:
    """Build a consistent two-column label/value table used throughout the report."""
    table = Table(rows, colWidths=[7 * cm, 8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), _MUTED_COLOR),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    return table


def _data_table(header: list[str], rows: list[list[str]]) -> Table:
    """Build a full data table (header row + body rows) with consistent styling."""
    table = Table([header] + rows, colWidths=None, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _image_flowable(png_bytes: bytes | None, width: float = 15 * cm) -> Image | None:
    """Wrap PNG bytes in a ReportLab Image flowable, scaled to a fixed width, or None if unavailable."""
    if png_bytes is None:
        return None
    return Image(io.BytesIO(png_bytes), width=width, height=width * 0.55)


def build_portfolio_report_pdf(data: ReportData) -> bytes:
    """
    Build the complete Portfolio Report PDF and return it as bytes.
    Every number is read directly from `data` (already fully computed
    by report_generator.py); this function only lays it out.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.2 * cm, bottomMargin=2 * cm,
    )
    story = []

    # ---------------- Cover ----------------
    story.append(_logo_placeholder())
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"{APP_TITLE} — Portfolio Report", _TITLE_STYLE))
    story.append(Paragraph(f"Prepared for {data.username} • Generated {format_datetime(data.generated_at)}", _SUBTITLE_STYLE))

    # ---------------- Portfolio Summary ----------------
    story.append(Paragraph("Portfolio Summary", _SECTION_STYLE))
    story.append(
        _metric_table(
            [
                ("Total Investment", format_currency(data.total_investment, "₹")),
                ("Current Value", format_currency(data.current_value, "₹")),
                ("Total Profit/Loss", f"{format_currency(data.total_profit_loss, '₹')} ({format_percentage(data.total_profit_loss_pct)})"),
                ("Today's Gain/Loss", format_currency(data.todays_gain_loss, "₹")),
                ("Number of Holdings", str(data.holdings_count)),
            ]
        )
    )

    if data.holdings:
        story.append(Spacer(1, 0.4 * cm))
        story.append(
            _data_table(
                ["Ticker", "Qty", "Avg. Buy Price", "Current Price", "Current Value", "P&L %"],
                [
                    [
                        h["ticker_symbol"], f"{h['quantity']:g}",
                        format_currency(h["average_buy_price"], "₹"), format_currency(h["current_price"], "₹"),
                        format_currency(h["current_value"], "₹"), format_percentage(h["profit_loss_pct"]),
                    ]
                    for h in data.holdings
                ],
            )
        )

    # ---------------- Top Winners & Losers ----------------
    story.append(Paragraph("Top Winners & Losers", _SECTION_STYLE))
    if data.top_winner or data.top_loser:
        winner_row = f"{data.top_winner['ticker_symbol']} ({format_percentage(data.top_winner['profit_loss_pct'])})" if data.top_winner else "N/A"
        loser_row = f"{data.top_loser['ticker_symbol']} ({format_percentage(data.top_loser['profit_loss_pct'])})" if data.top_loser else "N/A"
        story.append(_metric_table([("Top Winner", winner_row), ("Top Loser", loser_row)]))

    winners = sorted(data.holdings, key=lambda h: h["profit_loss_pct"], reverse=True)[:3]
    losers = sorted(data.holdings, key=lambda h: h["profit_loss_pct"])[:3]
    winners_losers_img = _image_flowable(
        render_winners_losers_image(
            [{"ticker": h["ticker_symbol"], "pnl_pct": h["profit_loss_pct"]} for h in winners],
            [{"ticker": h["ticker_symbol"], "pnl_pct": h["profit_loss_pct"]} for h in losers],
        )
    )
    if winners_losers_img:
        story.append(Spacer(1, 0.3 * cm))
        story.append(winners_losers_img)

    story.append(PageBreak())

    # ---------------- Allocation ----------------
    story.append(Paragraph("Asset Allocation", _SECTION_STYLE))
    story.append(_metric_table([("Diversification Score", f"{data.diversification_score:.0f}/100 ({data.concentration_label})")]))
    allocation_img = _image_flowable(render_allocation_pie_image(data.allocation_weights))
    if allocation_img:
        story.append(Spacer(1, 0.3 * cm))
        story.append(allocation_img)

    story.append(Paragraph("Sector Allocation", _SECTION_STYLE))
    sector_img = _image_flowable(render_sector_bar_image(data.sector_weights))
    if sector_img:
        story.append(sector_img)
    else:
        story.append(Paragraph("No sector data available.", _BODY_STYLE))

    # ---------------- Portfolio Performance ----------------
    story.append(Paragraph("Portfolio Performance", _SECTION_STYLE))
    growth_img = _image_flowable(render_growth_line_image(data.transactions))
    if growth_img:
        story.append(growth_img)
    else:
        story.append(Paragraph("No transaction history available yet.", _BODY_STYLE))

    story.append(PageBreak())

    # ---------------- Risk & Performance Metrics ----------------
    story.append(Paragraph("Risk & Performance Metrics", _SECTION_STYLE))
    story.append(
        _metric_table(
            [
                ("Risk Score", f"{data.risk_score:.0f}/100 ({data.risk_label})"),
                ("Portfolio Health Score", f"{data.health_score:.0f}/100 ({data.health_label})"),
                ("Expected Return", format_percentage(data.expected_return_pct) if data.expected_return_pct is not None else "N/A"),
                ("Volatility", format_percentage(data.volatility_pct) if data.volatility_pct is not None else "N/A"),
                ("Sharpe Ratio", f"{data.sharpe_ratio:.2f}" if data.sharpe_ratio is not None else "N/A"),
                ("Beta", f"{data.beta:.2f}" if data.beta is not None else "N/A"),
                ("Max Drawdown", format_percentage(data.max_drawdown_pct) if data.max_drawdown_pct is not None else "N/A"),
            ]
        )
    )
    risk_img = _image_flowable(render_risk_gauge_image(data.risk_score, data.risk_label), width=12 * cm)
    if risk_img:
        story.append(Spacer(1, 0.3 * cm))
        story.append(risk_img)

    # ---------------- Dividend Summary ----------------
    story.append(Paragraph("Dividend Summary", _SECTION_STYLE))
    story.append(
        _metric_table(
            [
                ("Estimated Annual Dividend Income", format_currency(data.dividend_total_estimated, "₹")),
                ("Portfolio Average Yield", format_percentage(data.dividend_average_yield_pct)),
            ]
        )
    )

    story.append(PageBreak())

    # ---------------- Recommendation Summary ----------------
    story.append(Paragraph("Recommendation Summary", _SECTION_STYLE))
    for line in data.recommendation_summary.split("\n\n"):
        if line.strip():
            story.append(Paragraph(line.replace("**", ""), _BODY_STYLE))
            story.append(Spacer(1, 0.15 * cm))

    # ---------------- AI Assistant Summary ----------------
    story.append(Paragraph("AI Assistant Summary", _SECTION_STYLE))
    for line in data.ai_assistant_summary.split("\n\n"):
        if line.strip():
            story.append(Paragraph(line.replace("**", ""), _BODY_STYLE))
            story.append(Spacer(1, 0.15 * cm))

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "This report was generated automatically by FinSight AI using live and cached market data. "
        "It is provided for informational purposes only and does not constitute financial advice.",
        ParagraphStyle("Disclaimer", parent=_BODY_STYLE, textColor=_MUTED_COLOR, fontSize=8),
    ))

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buffer.seek(0)
    return buffer.read()
