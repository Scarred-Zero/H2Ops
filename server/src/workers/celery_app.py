import os
from celery import Celery
from src.core.config import settings

celery_broker_url = settings.CELERY_BROKER_URL
celery_result_backend = settings.CELERY_RESULT_BACKEND

celery_app = Celery(
    "H2Ops",
    broker=celery_broker_url,
    backend=celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30-minute hard cap for large video processing
    task_soft_time_limit=1500,
)

try:
    import src.workers.tasks  # noqa: F401
except Exception:  # pragma: no cover
    pass
