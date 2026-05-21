from celery import Celery
from celery.signals import worker_process_init

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


@worker_process_init.connect
def _configure_worker_logging(**_kwargs: object) -> None:
    from app.observability import configure_log_shippers, configure_logging

    configure_logging(log_level=settings.log_level, env=settings.app_env)
    configure_log_shippers(
        loki_url=settings.loki_url,
        elasticsearch_url=settings.elasticsearch_url,
        labels={
            "app": "autoflowops",
            "service": "worker",
            "env": settings.app_env,
        },
    )
