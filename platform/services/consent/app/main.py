from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()

_CONSENTS: dict[str, dict] = {}


class CreateConsent(BaseModel):
    contact_id: str
    status: str
    proof_source: str


@app.post("/consents", status_code=status.HTTP_201_CREATED)
def create_consent(payload: CreateConsent):
    _CONSENTS[payload.contact_id] = payload.model_dump()
    return payload.model_dump()


@app.get("/consents/{contact_id}/eligibility")
def get_eligibility(contact_id: str):
    consent = _CONSENTS.get(contact_id)
    return {"contact_id": contact_id, "eligible": bool(consent and consent["status"] == "opted_in")}
