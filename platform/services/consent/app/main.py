from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import Consent
from shared.db.session import get_db

router = APIRouter(prefix="/consents")


class CreateConsent(BaseModel):
    contact_id: str
    status: str
    proof_source: str


@router.post("", status_code=status.HTTP_201_CREATED)
def create_consent(payload: CreateConsent, db: Session = Depends(get_db)):
    consent = Consent(
        contact_id=payload.contact_id,
        status=payload.status,
        proof_source=payload.proof_source,
    )
    db.add(consent)
    db.commit()
    return {"contact_id": consent.contact_id, "status": consent.status, "proof_source": consent.proof_source}


@router.get("/{contact_id}/eligibility")
def get_eligibility(contact_id: str, db: Session = Depends(get_db)):
    consent = (
        db.query(Consent)
        .filter(Consent.contact_id == contact_id)
        .order_by(Consent.id.desc())
        .first()
    )
    return {"contact_id": contact_id, "eligible": bool(consent and consent.status == "opted_in")}


app = FastAPI()
app.include_router(router)
