import logging
import os
import subprocess
import tempfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image

from src.workers.celery_app import celery_app
from src.core.config import settings


logger = logging.getLogger(__name__)


def _send_smtp_email(to_email: str, subject: str, html_content: str) -> None:
    if not getattr(settings, "SMTP_HOST", None):
        logger.info(
            f"\n=== [DEV EMAIL LOG] ===\nTo: {to_email}\nSubject: {subject}\nContent:\n{html_content}\n======================="
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAILS_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if getattr(settings, "SMTP_USE_TLS", True):
            server.starttls()
        if getattr(settings, "SMTP_USER", None):
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAILS_FROM_EMAIL, [to_email], msg.as_string())


@celery_app.task(name="send_verification_email_task", bind=True, max_retries=3)
def send_verification_email_task(self, email_to: str, token: str) -> None:
    frontend_url = getattr(
        settings, "FRONTEND_VERIFY_URL", "http://localhost:3000/verify-email"
    )
    verify_url = f"{frontend_url}?token={token}"

    if getattr(settings, "ENVIRONMENT", "development") == "development" or not getattr(
        settings, "SMTP_HOST", None
    ):
        logger.info(f"Dev verification link for {email_to}: {verify_url}")
        return

    try:
        subject = "Confirm Your Account - H2Ops"
        html_content = f"<h2>Welcome!</h2><p>Verify your account: <a href='{verify_url}'>Click here</a></p>"
        _send_smtp_email(email_to, subject, html_content)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="send_password_reset_email_task", bind=True, max_retries=3)
def send_password_reset_email_task(self, email_to: str, token: str) -> None:
    frontend_url = getattr(
        settings, "FRONTEND_RESET_PASSWORD", "http://localhost:3000/auth/reset-password"
    )
    reset_url = f"{frontend_url}?token={token}"

    if getattr(settings, "ENVIRONMENT", "development") == "development" or not getattr(
        settings, "SMTP_HOST", None
    ):
        logger.info(f"Dev password reset link for {email_to}: {reset_url}")
        return

    try:
        subject = "Reset Your Password - H2Ops"
        html_content = f"<h2>Reset Password</h2><p>Reset your password: <a href='{reset_url}'>Click here</a></p>"
        _send_smtp_email(email_to, subject, html_content)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
