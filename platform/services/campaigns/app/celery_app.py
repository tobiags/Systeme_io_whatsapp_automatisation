"""Celery application instance for the campaign scheduler.

The broker and result backend are both Redis, configured via the
REDIS_URL environment variable (default: redis://localhost:6379/0).
"""
import os

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "campaigns",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.campaigns.app.tasks",
        "services.integrations.app.sync_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Retry a failed task up to 3 times with exponential back-off.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "dispatch-daily-broadcasts": {
            "task": "campaigns.dispatch_daily_broadcasts",
            "schedule": crontab(minute="*/10"),
        },
        "sync-systemeio-contacts-daily": {
            "task": "integrations.sync_systemeio_contacts",
            # Every day at 07:00 UTC (before the 09:00 local broadcast)
            "schedule": crontab(hour=7, minute=0),
        },
    },
)
