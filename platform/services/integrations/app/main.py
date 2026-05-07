from fastapi import APIRouter, Depends, FastAPI, status
from sqlalchemy.orm import Session

from shared.db.models import Consent, Contact, InboundMessage
from shared.db.session import get_db
from services.conversation_ai.app.service import build_reply
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


@router.post("/wati", status_code=status.HTTP_202_ACCEPTED)
def wati_inbound(payload: dict, db: Session = Depends(get_db)):
    """
    Receive an inbound WhatsApp message from Wati.

    Wati webhook payload shape (simplified):
        { "waId": "33612345678", "text": { "body": "Bonjour ..." }, ... }

    Steps:
    1. Extract phone + message text.
    2. Look up contact by phone (contact_id may be null for unknown numbers).
    3. Call conversation_ai to generate a reply.
    4. Persist the inbound message with the AI reply.
    5. Return the reply so Wati can be configured to act on it (or n8n can relay it).
    """
    phone = payload.get("waId") or payload.get("phone") or ""
    # Wati wraps text under "text.body"; some integrations send a flat "body"
    text_obj = payload.get("text") or {}
    text = (text_obj.get("body") if isinstance(text_obj, dict) else None) or payload.get("body", "")

    if not phone or not text:
        return {"status": "ignored", "reason": "missing phone or text"}

    # Resolve contact (optional — message is stored even for unknown numbers)
    contact = db.query(Contact).filter(Contact.phone == phone).first()
    contact_id = contact.id if contact else None

    # AI reply
    result = build_reply(text)

    # Persist
    inbound = InboundMessage(
        phone=phone,
        contact_id=contact_id,
        text=text,
        ai_reply=result["reply"],
        needs_human=result.get("needs_human", False),
        intent=result.get("intent", "default"),
    )
    db.add(inbound)
    db.commit()
    db.refresh(inbound)

    return {
        "id": inbound.id,
        "phone": phone,
        "contact_id": contact_id,
        "reply": result["reply"],
        "needs_human": result["needs_human"],
        "intent": result["intent"],
    }


@router.post("/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(payload: dict):
    return handle_session(payload)


app = FastAPI()
app.include_router(router)
