from fastapi import FastAPI
from pydantic import BaseModel

from services.conversation_ai.app.service import build_reply

app = FastAPI()


class AIRequest(BaseModel):
    contact_id: str
    message: str


@app.post("/ai/reply")
def ai_reply(payload: AIRequest):
    result = build_reply(payload.message)
    return {"contact_id": payload.contact_id, **result}
