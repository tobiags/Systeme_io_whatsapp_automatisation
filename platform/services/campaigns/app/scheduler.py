"""Edition scheduler for timed challenge reminders.

When a StreamYard session is registered, the system schedules automatically:
  - Broadcast  -> broadcast_campaign_impl (H-8 before live, or immediately if late)
  - H-2h       -> live_day{N}_h2 (3-way behavioral branching)
  - H-10m      -> live_day{N}_h10
  - H+5m       -> live_day{N}_hplus5
  - H+2h (J3)  -> live_day3_offer_hplus2
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.tasks import (
    dispatch_broadcast,
    dispatch_h2,
    dispatch_h10,
    dispatch_h_plus_2,
    dispatch_h_plus_5,
)

logger = logging.getLogger(__name__)


_OFFSETS: list[tuple[str, timedelta, object, int | None]] = [
    ("h2", timedelta(hours=-2), dispatch_h2, None),
    ("h10", timedelta(minutes=-10), dispatch_h10, None),
    ("h_plus_5", timedelta(minutes=5), dispatch_h_plus_5, None),
    ("h_plus_2", timedelta(hours=2), dispatch_h_plus_2, 3),
]

_CHALLENGE_DAYS = [1, 2, 3]


def schedule_edition(
    campaign_key: str,
    edition_key: str,
    cohort: str,
    edition_date: str,
    streamyard_url: str = "",
    day_number: int | None = None,
) -> list[dict]:
    """Schedule all timed dispatch tasks for the given edition."""
    cohort_config = get_cohort_config(cohort)
    tz = ZoneInfo(cohort_config["timezone"])
    live_time_str = cohort_config["live_time"]
    live_hour, live_minute = (int(x) for x in live_time_str.split(":"))

    start_date = datetime.strptime(edition_date, "%Y-%m-%d").date()
    scheduled: list[dict] = []

    challenge_days = [day_number] if day_number in _CHALLENGE_DAYS else _CHALLENGE_DAYS

    for current_day_number in challenge_days:
        live_date = start_date + timedelta(days=current_day_number - 1)
        live_dt_local = datetime(
            live_date.year,
            live_date.month,
            live_date.day,
            live_hour,
            live_minute,
            tzinfo=tz,
        )
        live_dt_utc = live_dt_local.astimezone(timezone.utc)

        # ── Auto-broadcast: H-8 before live, fire immediately if late ──────────
        # This replaces the manual curl /campaigns/broadcast.
        # If the ops page is submitted before H-8 → scheduled.
        # If submitted after H-8 (admin running late) → fires in 10 seconds.
        broadcast_eta = live_dt_utc + timedelta(hours=-8)
        local_date_str = live_date.isoformat()
        broadcast_kwargs = {
            "campaign_key": campaign_key,
            "cohort": cohort,
            "edition_key": edition_key,
            "local_date_str": local_date_str,
        }
        now = datetime.now(timezone.utc)
        if broadcast_eta > now:
            bcast_result = dispatch_broadcast.apply_async(
                kwargs=broadcast_kwargs,
                eta=broadcast_eta,
            )
            scheduled.append({
                "task": "dispatch_broadcast",
                "day": current_day_number,
                "eta": broadcast_eta.isoformat(),
                "task_id": bcast_result.id,
            })
            logger.info("Broadcast scheduled for day%d at %s", current_day_number, broadcast_eta.isoformat())
        else:
            # ETA already past — fire in 10s (admin submitted ops page late)
            bcast_result = dispatch_broadcast.apply_async(
                kwargs=broadcast_kwargs,
                countdown=10,
            )
            scheduled.append({
                "task": "dispatch_broadcast",
                "day": current_day_number,
                "eta": "immediate",
                "task_id": bcast_result.id,
            })
            logger.info("Broadcast firing immediately for day%d (H-8 was past)", current_day_number)

        # ── Timed reminders (H-2, H-10, H+5, H+2) ──────────────────────────
        for timing_key, offset, task, day_only in _OFFSETS:
            if day_only is not None and current_day_number != day_only:
                continue

            eta = live_dt_utc + offset
            now = datetime.now(timezone.utc)
            if eta <= now:
                logger.warning(
                    "Skipping %s day%d %s - ETA %s is in the past",
                    edition_key,
                    current_day_number,
                    timing_key,
                    eta.isoformat(),
                )
                continue

            result = task.apply_async(
                kwargs={
                    "campaign_key": campaign_key,
                    "cohort": cohort,
                    "day_number": current_day_number,
                    "edition_key": edition_key,
                    "streamyard_url": "",
                },
                eta=eta,
            )
            desc = {
                "task": f"dispatch_{timing_key}",
                "day": current_day_number,
                "eta": eta.isoformat(),
                "task_id": result.id,
            }
            scheduled.append(desc)
            logger.info("Scheduled %s", desc)

    return scheduled
