COHORT_CONFIG = {
    "EU": {
        "live_time": "21:00",
        "live_time_label": "21h (heure de Paris / Berlin)",
        # broadcast_time = H-2 before live → 19:00 local.
        # The heartbeat (dispatch_daily_broadcasts, every 10 min) fires the
        # DAY_N broadcast at this time. H-10 reminders fire relative
        # to live_time regardless of broadcast_time.
        "broadcast_time": "19:00",
        "timezone": "Europe/Paris",
        "live_timezone": "Europe/Paris",
    },
    "US-CA": {
        "live_time": "19:00",
        "live_time_label": "19h (heure de New-York / Montréal)",
        # broadcast_time = H-2 before live → 17:00 local.
        "broadcast_time": "17:00",
        "timezone": "America/Montreal",
        "live_timezone": "America/Montreal",
    },
}


def get_cohort_config(region: str) -> dict:
    return COHORT_CONFIG.get(region, COHORT_CONFIG["EU"])
