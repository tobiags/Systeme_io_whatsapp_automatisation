"""Edition scheduler for timed challenge reminders.

When a StreamYard session is registered via the OPS page, the system:
  - Schedules the daily BROADCAST via dispatch_broadcast (H-2 before live,
    or immediately if the ops page was submitted after H-2).
  - Records the expected time for H-10m — fired by
    the heartbeat task `dispatch_daily_broadcasts` (every 10 min, AuditEvent
    idempotency) rather than ETA Celery tasks, which are silently dropped by
    the Redis broker when the delay exceeds the visibility_timeout.

NOTE: H-2h is intentionally excluded — it uses the same template keys as the
daily broadcast and would create duplicate messages.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.tasks import dispatch_broadcast

logger = logging.getLogger(__name__)


# Only used for recording expected times (not for creating ETA tasks).
# Only H-10 is recorded here; H-2/H+90 Day 3 are handled by the heartbeat task.
_OFFSETS: list[tuple[str, timedelta, object, int | None]] = [
    ("h10", timedelta(minutes=-10), None, None),
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

        # ── Auto-broadcast: broadcast_time in COHORT_CONFIG (H-2 before live,
        # except Day 3 which uses day3_broadcast_time — pulled forward so it
        # doesn't land at the same clock time as the Day-3-only H-2 reminder).
        # Primary mechanism: the heartbeat (dispatch_daily_broadcasts, every 10 min)
        # fires the broadcast once local_now >= broadcast_time.
        # This ETA task is a belt-and-suspenders backup for the case where the ops
        # page is submitted close to broadcast_time and the heartbeat hasn't ticked yet.
        # NOTE: Redis broker silently drops ETA tasks scheduled >visibility_timeout
        # away (~1h). For ops pages submitted more than 1h before broadcast_time, the
        # ETA task will be dropped — the heartbeat covers that case reliably.
        broadcast_time_key = "day3_broadcast_time" if current_day_number == 3 else "broadcast_time"
        broadcast_time_str = cohort_config.get(broadcast_time_key, "09:00")
        b_hour, b_minute = (int(x) for x in broadcast_time_str.split(":"))
        broadcast_dt_local = datetime(
            live_date.year, live_date.month, live_date.day, b_hour, b_minute, tzinfo=tz,
        )
        broadcast_eta = broadcast_dt_local.astimezone(timezone.utc)
        local_date_str = live_date.isoformat()
        broadcast_kwargs = {
            "campaign_key": campaign_key,
            "cohort": cohort,
            "edition_key": edition_key,
            "local_date_str": local_date_str,
        }
        now = datetime.now(timezone.utc)
        today_local = datetime.now(tz).date()
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
            logger.info("Broadcast ETA set for day%d at %s (%s)", current_day_number, broadcast_eta.isoformat(), broadcast_time_key)
        elif live_date >= today_local:
            # ETA already past but the challenge day itself is today (or later,
            # e.g. same-day broadcast_time already elapsed) — the ops page was
            # submitted after broadcast_time, so fire in 10s instead of dropping it.
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
            logger.info("Broadcast firing immediately for day%d (ops page submitted after %s)", current_day_number, broadcast_time_key)
        else:
            # The challenge day itself has already elapsed (e.g. a wholly past
            # edition) — nothing should be scheduled or fired for it.
            logger.info("Skipping broadcast for day%d: live_date %s already elapsed", current_day_number, live_date.isoformat())

        # ── Timed reminders (H-10; H-2/H+90 handled by heartbeat) ───────────────
        # NOTE: ETA-based task scheduling does NOT work reliably with a Redis
        # broker (tasks beyond the visibility_timeout are silently dropped).
        # Timed reminders are now handled by the heartbeat task
        # `dispatch_daily_broadcasts` (runs every 10 min) which calls
        # `_dispatch_timed_reminders()` with AuditEvent idempotency.
        # We only record the expected times here for informational purposes.
        for timing_key, offset, _task, day_only in _OFFSETS:
            if day_only is not None and current_day_number != day_only:
                continue
            eta = live_dt_utc + offset
            now = datetime.now(timezone.utc)
            if eta <= now:
                continue
            scheduled.append({
                "task": f"dispatch_{timing_key}",
                "day": current_day_number,
                "eta": eta.isoformat(),
                "task_id": "heartbeat",  # handled by dispatch_daily_broadcasts
                "note": "fired by heartbeat, not ETA task",
            })
            logger.info(
                "Reminder %s day%d eta=%s will fire via heartbeat (ETA tasks disabled for Redis)",
                timing_key, current_day_number, eta.isoformat(),
            )

    return scheduled
