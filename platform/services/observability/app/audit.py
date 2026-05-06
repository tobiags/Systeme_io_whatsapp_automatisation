from datetime import datetime, timezone

AUDIT_LOG: list[dict] = []


def append_event(name: str, aggregate_id: str, payload: dict) -> dict:
    event = {
        "name": name,
        "aggregate_id": aggregate_id,
        "payload": payload,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT_LOG.append(event)
    return event


def list_events() -> list[dict]:
    return AUDIT_LOG
