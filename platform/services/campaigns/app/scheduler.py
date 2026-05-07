"""Edition scheduler — schedules all Celery tasks for a challenge edition.

Called when a StreamYard session is registered via /webhooks/streamyard/session.
For each of the 3 live days it schedules:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Day N live time (UTC)  │  Task              │  Template key        │
  ├─────────────────────────┼────────────────────┼──────────────────────┤
  │  live_dt - 6 h          │  dispatch_h6       │  dayN_prelive_h6     │
  │  live_dt - 45 min       │  dispatch_h45      │  dayN_prelive_h45    │
  │  live_dt - 10 min       │  dispatch_h10      │  dayN_prelive_h10    │
  │  live_dt + 30 min       │  dispatch_recap    │  dayN_postlive_recap │
  └─────────────────────────────────────────────────────────────────────┘

`live_dt` for each day is derived from the edition start date +
the cohort's configured live time in UTC.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.tasks import dispatch_h10, dispatch_h45, dispatch_h6, dispatch_recap

logger = logging.getLogger(__name__)

# Timedeltas relative to live_dt for each dispatch
_OFFSETS: list[tuple[str, timedelta, object]] = [
    ("h6",    timedelta(hours=-6),     dispatch_h6),
    ("h45",   timedelta(minutes=-45),  dispatch_h45),
    ("h10",   timedelta(minutes=-10),  dispatch_h10),
    ("recap", timedelta(minutes=30),   dispatch_recap),
]

# The challenge runs for 3 consecutive days starting on edition_date.
_CHALLENGE_DAYS = [1, 2, 3]


def schedule_edition(
    campaign_key: str,
    edition_key: str,
    cohort: str,
    edition_date: str,        # ISO date string, e.g. "2026-05-08"
    streamyard_url: str = "",
) -> list[dict]:
    """Schedule all timed dispatch tasks for the given edition.

    Returns a list of scheduled task descriptors (useful for logging and tests).
    """
    cohort_config = get_cohort_config(cohort)
    tz = ZoneInfo(cohort_config["timezone"])
    live_time_str = cohort_config["live_time"]  # e.g. "21:00"
    live_hour, live_minute = (int(x) for x in live_time_str.split(":"))

    # Parse edition start date.
    start_date = datetime.strptime(edition_date, "%Y-%m-%d").date()

    scheduled: list[dict] = []

    for day_number in _CHALLENGE_DAYS:
        # Build the aware local datetime for this day's live session.
        live_date = start_date + timedelta(days=day_number - 1)
        live_dt_local = datetime(
            live_date.year, live_date.month, live_date.day,
            live_hour, live_minute,
            tzinfo=tz,
        )
        live_dt_utc = live_dt_local.astimezone(timezone.utc)

        for timing_key, offset, task in _OFFSETS:
            eta = live_dt_utc + offset
            now = datetime.now(timezone.utc)
            if eta <= now:
                logger.warning(
                    "Skipping %s day%d %s — ETA %s is in the past",
                    edition_key, day_number, timing_key, eta.isoformat(),
                )
                continue

            result = task.apply_async(
                kwargs={
                    "campaign_key": campaign_key,
                    "cohort": cohort,
                    "day_number": day_number,
                    "edition_key": edition_key,
                    "streamyard_url": streamyard_url if timing_key == "h45" else "",
                },
                eta=eta,
            )
            desc = {
                "task": f"dispatch_{timing_key}",
                "day": day_number,
                "eta": eta.isoformat(),
                "task_id": result.id,
            }
            scheduled.append(desc)
            logger.info("Scheduled %s", desc)

    return scheduled
