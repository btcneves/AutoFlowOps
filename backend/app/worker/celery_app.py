from celery import Celery

from app.config import settings

celery_app = Celery(
    "autoflowops",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    result_serializer="json",
    task_serializer="json",
    task_track_started=True,
    timezone=settings.default_timezone,
)
