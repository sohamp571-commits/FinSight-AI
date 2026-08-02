"""
market_intelligence/email_notification.py

Purpose: SMTP-based email delivery for instant alerts and daily/weekly
digests. Uses Python's standard-library `smtplib`/`email` (no extra
dependency needed) and reads SMTP credentials from the existing
`config.py` environment-variable pattern -- new SMTP_* variables are
documented here and should be added to `.env` the same way
NEWS_API_KEY was in Phase 1 (this file reads them defensively via
`os.getenv` so it degrades gracefully, exactly like `news_fetcher.py`
does for a missing `NEWS_API_KEY`, if they're never configured).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from logging_config import logger

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_ADDRESS = os.getenv("SMTP_FROM_ADDRESS", "noreply@finsight.ai")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("1", "true", "yes")


def is_email_configured() -> bool:
    """Whether SMTP credentials are present. Every send function no-ops safely if not."""
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)


def _send_email(to_address: str, subject: str, html_body: str) -> bool:
    """
    Send a single HTML email via SMTP. Returns True on success, False
    on any failure (logged, never raised -- an email delivery failure
    must never break the surrounding notification flow).
    """
    if not is_email_configured():
        logger.warning(f"SMTP is not configured; skipping email to {to_address} ('{subject}').")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SMTP_FROM_ADDRESS
    message["To"] = to_address
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_ADDRESS, [to_address], message.as_string())
        logger.info(f"Email sent to {to_address}: '{subject}'")
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error(f"Failed to send email to {to_address}: {exc}")
        return False


def _wrap_html(inner_html: str, title: str) -> str:
    """Wrap inner content in a minimal, consistent HTML email shell."""
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0E1117; color: #E2E8F0; padding: 24px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1E293B; border-radius: 12px; padding: 24px;">
          <h2 style="color: #4F8BF9; margin-top: 0;">📈 FinSight AI</h2>
          <h3>{title}</h3>
          {inner_html}
          <p style="font-size: 12px; opacity: 0.6; margin-top: 24px;">
            You're receiving this because of your FinSight AI notification preferences.
            Manage them anytime from your account settings.
          </p>
        </div>
      </body>
    </html>
    """


def send_instant_alert_email(to_address: str, title: str, message: str) -> bool:
    """Send a single instant-alert email (e.g. a price alert or IPO open notice)."""
    inner = f"<p style='font-size: 15px; line-height: 1.5;'>{message}</p>"
    return _send_email(to_address, f"FinSight AI Alert: {title}", _wrap_html(inner, title))


def send_daily_digest_email(to_address: str, notifications: list[dict]) -> bool:
    """Send a daily digest email summarizing a user's notifications from the last 24 hours."""
    if not notifications:
        return False

    items_html = "".join(
        f"<li style='margin-bottom:8px;'><strong>{n['title']}</strong><br>"
        f"<span style='opacity:0.8;'>{n['message']}</span></li>"
        for n in notifications
    )
    inner = f"<p>Here's what happened in the last 24 hours:</p><ul style='padding-left: 20px;'>{items_html}</ul>"
    return _send_email(to_address, f"Your FinSight AI Daily Digest ({len(notifications)} updates)", _wrap_html(inner, "Daily Digest"))


def send_weekly_digest_email(to_address: str, notifications: list[dict]) -> bool:
    """Send a weekly digest email summarizing a user's notifications from the last 7 days."""
    if not notifications:
        return False

    items_html = "".join(
        f"<li style='margin-bottom:8px;'><strong>{n['title']}</strong><br>"
        f"<span style='opacity:0.8;'>{n['message']}</span></li>"
        for n in notifications
    )
    inner = f"<p>Here's your weekly summary ({len(notifications)} updates):</p><ul style='padding-left: 20px;'>{items_html}</ul>"
    return _send_email(to_address, f"Your FinSight AI Weekly Digest ({len(notifications)} updates)", _wrap_html(inner, "Weekly Digest"))
