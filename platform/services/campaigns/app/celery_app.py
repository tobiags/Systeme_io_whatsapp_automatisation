"""Celery application instance for the campaign scheduler.

The broker and result backend are both Redis, configured via the
REDIS_URL environment variable (default: redis://localhost:6379/0).
"""
import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "campaigns",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.campaigns.app.tasks"],
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
)
