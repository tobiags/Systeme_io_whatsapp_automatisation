from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from services.conversation_ai.app.service import build_reply

router = APIRouter(prefix="/ai")


class AIRequest(BaseModel):
    contact_id: str
    message: str


@router.post("/reply")
def ai_reply(payload: AIRequest):
    result = build_reply(payload.message)
    return {"contact_id": payload.contact_id, **result}


app = FastAPI()
app.include_router(router)
