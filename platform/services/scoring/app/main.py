from fastapi import FastAPI
from pydantic import BaseModel

from services.scoring.app.rules import SCORE_RULES

app = FastAPI()


class ScoreRequest(BaseModel):
    contact_id: str
    events: list[str]


@app.post("/scores/calculate")
def calculate_score(payload: ScoreRequest):
    score = sum(SCORE_RULES.get(event, 0) for event in payload.events)
    return {"contact_id": payload.contact_id, "score": score}
