from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import Score
from shared.db.session import get_db
from services.scoring.app.rules import SCORE_RULES

router = APIRouter(prefix="/scores")


class ScoreRequest(BaseModel):
    contact_id: str
    events: list[str]


@router.post("/calculate")
def calculate_score(payload: ScoreRequest, db: Session = Depends(get_db)):
    score = sum(SCORE_RULES.get(event, 0) for event in payload.events)
    db.add(Score(contact_id=payload.contact_id, events=payload.events, score=score))
    db.commit()
    return {"contact_id": payload.contact_id, "score": score}


app = FastAPI()
app.include_router(router)
