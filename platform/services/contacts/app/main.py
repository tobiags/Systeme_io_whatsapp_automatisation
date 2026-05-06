from uuid import uuid4

from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()

_CONTACTS: dict[str, dict] = {}


class CreateContact(BaseModel):
    phone: str
    first_name: str | None = None
    source: str


@app.post("/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(payload: CreateContact):
    contact_id = f"ct_{uuid4().hex[:8]}"
    data = {"id": contact_id, **payload.model_dump()}
    _CONTACTS[contact_id] = data
    return data
