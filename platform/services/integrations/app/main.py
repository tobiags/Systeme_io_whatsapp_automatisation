from fastapi import APIRouter, Depends, FastAPI, status
from sqlalchemy.orm import Session

from shared.db.models import Consent, Contact
from shared.db.session import get_db
from services.integrations.app.connectors.streamyard import handle_session
from services.integrations.app.normalizer import normalize_systemeio

router = APIRouter(prefix="/webhooks")


@router.post("/systemeio", status_code=status.HTTP_202_ACCEPTED)
def systemeio_webhook(payload: dict, db: Session = Depends(get_db)):
    """
    Receive Systeme.io webhook, normalize, upsert contact and record opt-in consent.
    Returns the normalized event plus the created/updated contact id.
    """
    normalized = normalize_systemeio(payload)
    lead = normalized["payload"]

    phone = lead.get("phone")
    contact_id = None

    if phone:
        from uuid import uuid4
        existing = db.query(Contact).filter(Contact.phone == phone).first()
        if existing:
            if lead.get("first_name"):
                existing.first_name = lead["first_name"]
            existing.source = lead.get("source", "systemeio")
            db.commit()
            db.refresh(existing)
            contact_id = existing.id
        else:
            contact = Contact(
                id=f"ct_{uuid4().hex[:8]}",
                phone=phone,
                first_name=lead.get("first_name"),
                source=lead.get("source", "systemeio"),
            )
            db.add(contact)
            db.commit()
            db.refresh(contact)
            contact_id = contact.id

        # Record opt-in consent (Systeme.io registration = implicit opt-in)
        consent = Consent(
            contact_id=contact_id,
            status="opted_in",
            proof_source="systemeio_registration",
        )
        db.add(consent)
        db.commit()

    return {**normalized, "contact_id": contact_id}


@router.post("/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(payload: dict):
    return handle_session(payload)


app = FastAPI()
app.include_router(router)
