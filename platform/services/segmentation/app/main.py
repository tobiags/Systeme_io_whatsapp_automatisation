from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class SegmentRequest(BaseModel):
    contact_id: str
    score: int


@app.post("/segments/assign")
def assign_segment(payload: SegmentRequest):
    score = payload.score
    if score <= 20:
        segment = "froid"
    elif score <= 50:
        segment = "tiede"
    elif score <= 80:
        segment = "chaud"
    else:
        segment = "tres_chaud"
    return {"contact_id": payload.contact_id, "segment": segment}
