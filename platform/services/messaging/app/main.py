from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.db.models import Message
from shared.db.session import get_db
from services.messaging.app.providers.mock import MockProvider
from services.messaging.app.providers.wati import WatiProvider

router = APIRouter(prefix="/messages")


def _get_provider():
    """Return WatiProvider when credentials are configured, else MockProvider."""
    if settings.wati_api_url and settings.wati_api_token:
        return WatiProvider(settings.wati_api_url, settings.wati_api_token)
    return MockProvider()


class SendMessageRequest(BaseModel):
    contact_id: str
    template_key: str
    variables: dict[str, str] = {}


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
def send_message(payload: SendMessageRequest, db: Session = Depends(get_db)):
    provider = _get_provider()
    result = provider.send_template(payload.contact_id, payload.template_key, payload.variables)
    msg = Message(
        id=f"msg_{uuid4().hex[:8]}",
        contact_id=payload.contact_id,
        template_key=payload.template_key,
        variables=payload.variables,
        status=result.get("status", "queued"),
        provider=result.get("provider", "mock"),
    )
    db.add(msg)
    db.commit()
    return {"message_id": msg.id, "status": msg.status, **result}


app = FastAPI()
app.include_router(router)
