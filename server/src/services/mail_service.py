import logging
from src.workers.tasks import (
    send_verification_email_task,
    send_password_reset_email_task,
)

logger = logging.getLogger(__name__)


class MailService:
    @staticmethod
    def send_verification_email(email_to: str, token: str) -> None:
        """Enqueues verification email sending in Celery worker."""
        logger.info(f"Queuing verification email task for: {email_to}")
        send_verification_email_task.delay(email_to, token)

    @staticmethod
    def send_password_reset_email(email_to: str, token: str) -> None:
        """Enqueues password reset email sending in Celery worker."""
        logger.info(f"Queuing password reset email task for: {email_to}")
        send_password_reset_email_task.delay(email_to, token)
