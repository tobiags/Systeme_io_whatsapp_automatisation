from fastapi import FastAPI, status
from pydantic import BaseModel

from services.messaging.app.providers.mock import MockProvider

app = FastAPI()
provider = MockProvider()


class SendMessageRequest(BaseModel):
    contact_id: str
    template_key: str
    variables: dict[str, str]


@app.post("/messages/send", status_code=status.HTTP_202_ACCEPTED)
def send_message(payload: SendMessageRequest):
    return provider.send_template(payload.contact_id, payload.template_key, payload.variables)
