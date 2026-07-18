COHORT_CONFIG = {
    "EU": {
        "live_time": "21:00",
        "live_time_label": "21h (heure de Paris / Berlin)",
        # broadcast_time = H-2 before live → 19:00 local.
        # The heartbeat (dispatch_daily_broadcasts, every 10 min) fires the
        # DAY_N broadcast at this time. H-10 reminders fire relative
        # to live_time regardless of broadcast_time.
        "broadcast_time": "19:00",
        # Day 3 only: the H-2 timed reminder (live_day3_h2) already fires at
        # H-2 (19:00), so the Day 3 broadcast is pulled forward to keep a
        # real gap between the two messages instead of both landing at 19:00.
        "day3_broadcast_time": "15:00",
        "timezone": "Europe/Paris",
        "live_timezone": "Europe/Paris",
    },
    "US-CA": {
        "live_time": "19:00",
        "live_time_label": "19h (heure de New-York / Montréal)",
        # broadcast_time = H-2 before live → 17:00 local.
        "broadcast_time": "17:00",
        # Day 3 only — see EU comment above (H-2 reminder fires at 17:00).
        "day3_broadcast_time": "13:00",
        "timezone": "America/Montreal",
        "live_timezone": "America/Montreal",
    },
}


def get_cohort_config(region: str) -> dict:
    return COHORT_CONFIG.get(region, COHORT_CONFIG["EU"])
