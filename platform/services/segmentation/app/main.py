from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class SegmentRequest(BaseModel):
    contact_id: str
    score: int


@app.post("/segments/assign")
def assign_segment(payload: SegmentRequest):
    score = payload.score
    if score <= 15:
        segment = "froid"
    elif score <= 40:
        segment = "tiede"
    elif score <= 75:
        segment = "chaud"
    else:
        segment = "tres_chaud"
    return {"contact_id": payload.contact_id, "segment": segment}
