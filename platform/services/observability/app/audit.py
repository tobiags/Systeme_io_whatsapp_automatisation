from sqlalchemy.orm import Session

from shared.db.models import AuditEvent


def append_event(db: Session, name: str, aggregate_id: str, payload: dict) -> dict:
    event = AuditEvent(name=name, aggregate_id=aggregate_id, payload=payload)
    db.add(event)
    db.commit()
    db.refresh(event)
    return {
        "name": event.name,
        "aggregate_id": event.aggregate_id,
        "payload": event.payload,
        "recorded_at": event.recorded_at.isoformat(),
    }


def list_events(db: Session) -> list[dict]:
    events = db.query(AuditEvent).order_by(AuditEvent.id).all()
    return [
        {
            "name": e.name,
            "aggregate_id": e.aggregate_id,
            "payload": e.payload,
            "recorded_at": e.recorded_at.isoformat(),
        }
        for e in events
    ]
