from datetime import datetime, timezone

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import ContactScore, Score, ScoreEvent, Segment
from shared.db.session import get_db
from services.scoring.app.rules import SCORE_RULES

router = APIRouter(prefix="/scores")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _segment_for_score(score: int) -> str:
    if score <= 15:
        return "froid"
    elif score <= 40:
        return "tiede"
    elif score <= 75:
        return "chaud"
    else:
        return "tres_chaud"


class ScoreRequest(BaseModel):
    contact_id: str
    events: list[str]


class EventRequest(BaseModel):
    contact_id: str
    event_type: str


@router.post("/calculate")
def calculate_score(payload: ScoreRequest, db: Session = Depends(get_db)):
    """Legacy batch score calculator — stores a Score snapshot."""
    score = sum(SCORE_RULES.get(event, 0) for event in payload.events)
    db.add(Score(contact_id=payload.contact_id, events=payload.events, score=score))
    db.commit()
    return {"contact_id": payload.contact_id, "score": score}


@router.post("/events", status_code=status.HTTP_201_CREATED)
def record_event(payload: EventRequest, db: Session = Depends(get_db)):
    """
    Record a single engagement event for a contact.
    - Validates the event type against the scoring rules.
    - Appends a ScoreEvent log entry.
    - Upserts the ContactScore running total.
    - Auto-assigns the segment based on the new total.
    """
    points = SCORE_RULES.get(payload.event_type)
    if points is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event_type '{payload.event_type}'. Valid types: {list(SCORE_RULES)}",
        )

    # Append immutable event log
    db.add(ScoreEvent(
        contact_id=payload.contact_id,
        event_type=payload.event_type,
        points=points,
    ))

    # Upsert running total
    contact_score = (
        db.query(ContactScore)
        .filter(ContactScore.contact_id == payload.contact_id)
        .first()
    )
    if contact_score:
        contact_score.total_score += points
        contact_score.last_updated = _now()
    else:
        contact_score = ContactScore(
            contact_id=payload.contact_id,
            total_score=points,
            last_updated=_now(),
        )
        db.add(contact_score)

    db.flush()  # ensure total_score is visible before reading it
    new_total = contact_score.total_score

    # Auto-assign segment
    segment = _segment_for_score(new_total)
    db.add(Segment(contact_id=payload.contact_id, segment=segment, score=new_total))

    db.commit()

    return {
        "contact_id": payload.contact_id,
        "event_type": payload.event_type,
        "points": points,
        "total_score": new_total,
        "segment": segment,
    }


app = FastAPI()
app.include_router(router)
