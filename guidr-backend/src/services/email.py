"""Email service for sending 2FA codes."""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_2fa_code_email(to_email: str, code: str, purpose: str = "verification") -> bool:
    """Send a 2FA verification code via email.

    Args:
        to_email: Recipient email address
        code: 6-digit verification code
        purpose: Purpose of the code ('register' or 'password_reset')

    Returns:
        True if email sent successfully, False otherwise
    """
    if not settings.smtp_username or not settings.smtp_password:
        logger.error(
            "SMTP credentials not configured. "
            "Set SMTP_USERNAME and SMTP_PASSWORD in .env "
            "(use a Gmail App Password for Gmail accounts)."
        )
        return False

    logger.info(
        "Sending 2FA email to %s via %s:%d (user=%s)",
        to_email,
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_username,
    )

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your Guidr Verification Code"
        message["From"] = settings.email_from
        message["To"] = to_email

        if purpose == "register":
            purpose_text = "complete your registration"
        elif purpose == "password_reset":
            purpose_text = "reset your password"
        else:
            purpose_text = "verify your identity"

        logo_url = f"{settings.app_public_url.rstrip('/')}/images/guidr-logo.png"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Guidr Verification Code</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            <div style="background-color: #ffffff; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <img src="{logo_url}" alt="Guidr" style="max-width: 180px; height: auto; display: block; margin: 0 auto;" />
                </div>

                <h2 style="color: #333; font-size: 20px; margin-top: 0; margin-bottom: 20px;">Verification Code</h2>

                <p style="color: #666; font-size: 16px; margin-bottom: 30px;">Hello,</p>

                <p style="color: #666; font-size: 16px; margin-bottom: 30px;">
                    Please use the following verification code to {purpose_text}:
                </p>

                <div style="background-color: #F0EADC; border: 2px solid #FFD95D; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                    <div style="font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #576238; font-family: 'Courier New', monospace;">
                        {code}
                    </div>
                </div>

                <p style="color: #666; font-size: 14px; margin-bottom: 10px;">
                    This code will expire in 10 minutes.
                </p>

                <p style="color: #999; font-size: 14px; margin-top: 30px; margin-bottom: 0;">
                    If you didn't request this code, please ignore this email.
                </p>

                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

                <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
                    This is an automated message from Guidr. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""Guidr Verification Code

Hello,

Please use the following verification code to {purpose_text}:

{code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

---
This is an automated message from Guidr. Please do not reply to this email.
"""

        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        if settings.smtp_port == 465:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=True,
            )
        else:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=True,
            )

        logger.info("2FA code email sent to %s", to_email)
        return True

    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error(
            "SMTP authentication failed for %s — check SMTP_USERNAME and "
            "SMTP_PASSWORD (Gmail requires an App Password): %s",
            settings.smtp_username,
            e,
        )
        return False
    except aiosmtplib.SMTPConnectError as e:
        logger.error(
            "Could not connect to SMTP server %s:%d — %s",
            settings.smtp_host,
            settings.smtp_port,
            e,
        )
        return False
    except Exception as e:
        logger.error("Failed to send 2FA email to %s: %s", to_email, e)
        return False
