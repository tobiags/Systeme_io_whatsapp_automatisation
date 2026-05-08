import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from sqlalchemy.orm import Session

from shared.db.models import ChallengeEdition, Consent, Contact, InboundMessage
from shared.db.session import get_db
from services.conversation_ai.app.service import build_reply
from services.integrations.app.normalizer import normalize_systemeio

logger = logging.getLogger(__name__)

# Only attempt to schedule Celery tasks when Redis is reachable (not in tests).
_CELERY_ENABLED = bool(os.getenv("REDIS_URL"))

router = APIRouter(prefix="/webhooks")


@router.post("/systemeio", status_code=status.HTTP_202_ACCEPTED)
def systemeio_webhook(payload: dict, db: Session = Depends(get_db)):
    """
    Receive Systeme.io webhook, normalize, upsert contact and record opt-in consent.
    """
    normalized = normalize_systemeio(payload)
    lead = normalized["payload"]
    phone = lead.get("phone")
    contact_id = None

    if phone:
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

        db.add(Consent(
            contact_id=contact_id,
            status="opted_in",
            proof_source="systemeio_registration",
        ))
        db.commit()

    return {**normalized, "contact_id": contact_id}


@router.post("/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(payload: dict, db: Session = Depends(get_db)):
    """
    Register or update a StreamYard session for a challenge edition.
    The StreamYard join_url changes at every edition — this stores it so
    the messaging service can inject the right link in Day-1/2/3 messages.
    """
    edition_key = payload.get("edition_key", "")
    cohort = payload.get("region", "EU")
    join_url = payload.get("join_url")
    campaign_key = payload.get("challenge_key", "challenge-amazon-fba")

    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )
    if edition:
        if join_url:
            edition.streamyard_url = join_url
        db.commit()
    else:
        # Derive edition_date from edition_key (format: "YYYY-MM-DD-cohort")
        edition_date = "-".join(edition_key.split("-")[:3]) if edition_key else ""
        edition = ChallengeEdition(
            id=f"ed_{uuid4().hex[:8]}",
            campaign_key=campaign_key,
            edition_key=edition_key,
            cohort=cohort,
            edition_date=edition_date,
            streamyard_url=join_url,
        )
        db.add(edition)
        db.commit()
        db.refresh(edition)

    # Schedule timed dispatch tasks (H-6, H-45, H-10, post-live recap) when
    # Celery/Redis is available. Skipped in test environments without REDIS_URL.
    scheduled_count = 0
    if _CELERY_ENABLED and edition.edition_date:
        try:
            from services.campaigns.app.scheduler import schedule_edition
            scheduled = schedule_edition(
                campaign_key=campaign_key,
                edition_key=edition_key,
                cohort=cohort,
                edition_date=edition.edition_date,
                streamyard_url=join_url or "",
            )
            scheduled_count = len(scheduled)
        except Exception as exc:
            logger.error("Failed to schedule tasks for edition %s: %s", edition_key, exc)

    return {
        "challenge_key": campaign_key,
        "edition_key": edition_key,
        "region": cohort,
        "join_url": join_url,
        "stored": True,
        "tasks_scheduled": scheduled_count,
    }


@router.get("/streamyard/editions")
def list_editions(db: Session = Depends(get_db)):
    """List all registered challenge editions with their StreamYard links."""
    editions = (
        db.query(ChallengeEdition)
        .order_by(ChallengeEdition.created_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "edition_key": e.edition_key,
            "cohort": e.cohort,
            "edition_date": e.edition_date,
            "campaign_key": e.campaign_key,
            "streamyard_url": e.streamyard_url,
        }
        for e in editions
    ]


@router.post("/wati", status_code=status.HTTP_202_ACCEPTED)
def wati_inbound(payload: dict, db: Session = Depends(get_db)):
    """
    Receive an inbound WhatsApp message from Wati, call AI, persist reply.
    Wati payload: { "waId": "336...", "text": { "body": "..." } }
    """
    phone = payload.get("waId") or payload.get("phone") or ""
    # Wati v3 sends text as a plain string: {"waId": "...", "text": "hello", ...}
    # Some older integrations/tests send: {"text": {"body": "..."}}
    # Handle both formats.
    text_raw = payload.get("text")
    if isinstance(text_raw, str):
        text = text_raw
    elif isinstance(text_raw, dict):
        text = text_raw.get("body", "")
    else:
        text = payload.get("body", "")

    if not phone or not text:
        return {"status": "ignored", "reason": "missing phone or text"}

    contact = db.query(Contact).filter(Contact.phone == phone).first()
    contact_id = contact.id if contact else None

    result = build_reply(text)

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


def _intent_priority(intent: str) -> str:
    """
    Map a classified intent to an operator priority level.
    Spec §4 escalation rules:
      haute    — payment failure, installment request, explicit human call
      moyenne  — sceptic/trust objection, strong financial, persistent email issue
      faible   — simple FAQ, next challenge request, generic financial
    """
    if intent in {
        "payment_failure_followup_needed",
        "installment_plan_request",
        "human_escalation",
    }:
        return "haute"
    if intent in {
        "skeptic_trust_objection",
        "objection_financial_strong",
        "faq_email_missing",
    }:
        return "moyenne"
    return "faible"


@router.get("/wati/queue")
def wati_human_queue(db: Session = Depends(get_db)):
    """Return inbound messages that need human review, newest first, with priority."""
    rows = (
        db.query(InboundMessage)
        .filter(InboundMessage.needs_human.is_(True))
        .order_by(InboundMessage.received_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "phone": r.phone,
            "contact_id": r.contact_id,
            "text": r.text,
            "ai_reply": r.ai_reply,
            "intent": r.intent,
            "priority": _intent_priority(r.intent),
            "received_at": r.received_at.isoformat(),
        }
        for r in rows
    ]


app = FastAPI()
app.include_router(router)
