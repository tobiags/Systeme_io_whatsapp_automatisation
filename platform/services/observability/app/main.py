from fastapi import FastAPI, status
from pydantic import BaseModel

from services.observability.app.audit import append_event, list_events

app = FastAPI()


class AuditEvent(BaseModel):
    name: str
    aggregate_id: str
    payload: dict


@app.post("/audit/events", status_code=status.HTTP_201_CREATED)
def create_audit_event(payload: AuditEvent):
    return append_event(payload.name, payload.aggregate_id, payload.payload)


@app.get("/audit/events")
def get_audit_events():
    return list_events()
