from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.session import get_db
from services.observability.app.audit import append_event, list_events

router = APIRouter(prefix="/audit")


class AuditEventRequest(BaseModel):
    name: str
    aggregate_id: str
    payload: dict


@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_audit_event(payload: AuditEventRequest, db: Session = Depends(get_db)):
    return append_event(db, payload.name, payload.aggregate_id, payload.payload)


@router.get("/events")
def get_audit_events(db: Session = Depends(get_db)):
    return list_events(db)


app = FastAPI()
app.include_router(router)
