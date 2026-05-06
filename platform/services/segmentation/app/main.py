from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import Segment
from shared.db.session import get_db

router = APIRouter(prefix="/segments")


class SegmentRequest(BaseModel):
    contact_id: str
    score: int


@router.post("/assign")
def assign_segment(payload: SegmentRequest, db: Session = Depends(get_db)):
    score = payload.score
    if score <= 15:
        segment = "froid"
    elif score <= 40:
        segment = "tiede"
    elif score <= 75:
        segment = "chaud"
    else:
        segment = "tres_chaud"

    db.add(Segment(contact_id=payload.contact_id, segment=segment, score=score))
    db.commit()
    return {"contact_id": payload.contact_id, "segment": segment}


app = FastAPI()
app.include_router(router)
