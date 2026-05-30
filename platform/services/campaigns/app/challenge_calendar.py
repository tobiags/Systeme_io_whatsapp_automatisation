COHORT_CONFIG = {
    "EU": {
        "live_time": "21:00",
        # broadcast_time = H-2 before live → 19:00 local.
        # The heartbeat (dispatch_daily_broadcasts, every 10 min) fires the
        # DAY_N broadcast at this time. H-10 and H+5 reminders fire relative
        # to live_time regardless of broadcast_time.
        "broadcast_time": "19:00",
        "timezone": "Europe/Paris",
        "live_timezone": "Europe",
    },
    "US-CA": {
        "live_time": "19:00",
        # broadcast_time = H-2 before live → 17:00 local.
        "broadcast_time": "17:00",
        "timezone": "America/Montreal",
        "live_timezone": "America/Montreal",
    },
}


def get_cohort_config(region: str) -> dict:
    return COHORT_CONFIG.get(region, COHORT_CONFIG["EU"])
