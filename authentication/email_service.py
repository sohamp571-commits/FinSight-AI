

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import config
from logging_config import logger


class EmailService:
    """Handles sending emails."""

    @staticmethod
    def send_password_reset_email(
        recipient_email: str,
        reset_link: str,
    ) -> bool:
        """
        Send password reset email.

        Returns
        -------
        bool
            True if email sent successfully.
        """

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "FinSight AI - Password Reset"
            message["From"] = config.FROM_EMAIL
            message["To"] = recipient_email

            html = f"""
            <html>
            <body style="font-family:Arial,sans-serif;">
                <h2>FinSight AI</h2>

                <p>Hello,</p>

                <p>
                    We received a request to reset your password.
                </p>

                <p>
                    Click the button below to reset it.
                </p>

                <p>
                    <a href="{reset_link}"
                       style="
                       background:#2563eb;
                       color:white;
                       padding:12px 20px;
                       text-decoration:none;
                       border-radius:6px;">
                       Reset Password
                    </a>
                </p>

                <p>
                    If you did not request this,
                    simply ignore this email.
                </p>

                <hr>

                <small>
                FinSight AI<br>
                AI Powered Stock Market Intelligence Platform
                </small>

            </body>
            </html>
            """

            message.attach(MIMEText(html, "html"))

            server = smtplib.SMTP(
                config.SMTP_SERVER,
                config.SMTP_PORT
            )

            server.starttls()

            server.login(
                config.SMTP_EMAIL,
                config.SMTP_PASSWORD
            )

            server.sendmail(
                config.FROM_EMAIL,
                recipient_email,
                message.as_string(),
            )

            server.quit()

            logger.info(
                f"Password reset email sent to {recipient_email}"
            )

            return True

        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False