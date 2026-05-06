COHORT_CONFIG = {
    "EU": {
        "live_time": "21:00",
        "timezone": "Europe/Paris",
        "live_timezone": "Europe",
    },
    "US-CA": {
        "live_time": "19:00",
        "timezone": "America/Montreal",
        "live_timezone": "America/Montreal",
    },
}


def get_cohort_config(region: str) -> dict:
    return COHORT_CONFIG.get(region, COHORT_CONFIG["EU"])
