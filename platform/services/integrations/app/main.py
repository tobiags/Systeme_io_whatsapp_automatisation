import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from shared.db.models import ChallengeEdition, Consent, Contact, ContactScore, InboundMessage, Message, ScoreEvent, Segment
from shared.db.session import get_db
from services.conversation_ai.app.service import build_reply
from services.integrations.app.normalizer import normalize_systemeio
from services.scoring.app.rules import SCORE_RULES

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
    Receive a Wati webhook event. Wati sends ALL event types to the same URL.

    Handled event types (Context7 / Wati docs):
      messageReceived           — inbound message → AI reply + persist
      sentMessageDELIVERED_v2   — delivery confirmation → acknowledge
      sentMessageREAD_v2        — read receipt → record opened_message score
      templateMessageFailed     — template send failure → log warning

    Wati v3 payload for messageReceived:
        {"waId": "336...", "text": "...", "eventType": "messageReceived", ...}
    Legacy format (some integrations):
        {"waId": "336...", "text": {"body": "..."}}
    """
    event_type = payload.get("eventType") or payload.get("type") or "messageReceived"

    # ── Delivery confirmation ─────────────────────────────────────────────────
    if event_type == "sentMessageDELIVERED_v2":
        return {"status": "acknowledged", "eventType": event_type}

    # ── Read receipt → record opened_message score event ─────────────────────
    if event_type == "sentMessageREAD_v2":
        local_msg_id = payload.get("localMessageId", "")
        if local_msg_id:
            msg_row = db.query(Message).filter(Message.id == local_msg_id).first()
            if msg_row and msg_row.contact_id:
                db.add(ScoreEvent(
                    contact_id=msg_row.contact_id,
                    event_type="opened_message",
                    points=0,
                ))
                db.commit()
        return {"status": "acknowledged", "eventType": event_type}

    # ── Template send failure → log warning ──────────────────────────────────
    if event_type == "templateMessageFailed":
        # Context7 / Wati docs: real fields are failedCode + failedDetail
        logger.warning(
            "Wati template failed | waId=%s template=%s code=%s detail=%s",
            payload.get("waId", "?"),
            payload.get("templateName", payload.get("text", "?")),
            payload.get("failedCode", "?"),
            payload.get("failedDetail", "?"),
        )
        return {"status": "acknowledged", "eventType": event_type}

    # ── Inbound message (messageReceived / legacy) → AI reply ─────────────────
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


# ── Attendance tracking ───────────────────────────────────────────────────────

class RegistrantsPayload(BaseModel):
    """Batch StreamYard registration report for one challenge day.

    Submitted before or after a live session with the list of phones that
    registered on the StreamYard event page (regardless of actual attendance).
    Each phone gets a day{N}_streamyard_registered ScoreEvent (idempotent).

    This creates the MIDDLE branch of 3-way routing:
      day{N}_live_joined          → live_day{N}_attended
      day{N}_streamyard_registered (no live_joined) → live_day{N}_registered_absent
      neither                     → live_day{N}_not_registered
    """
    edition_key: str
    day_number: int = Field(..., ge=1, le=3)
    registrants: list[str]  # international phone numbers


class AttendancePayload(BaseModel):
    """Batch attendance report for one challenge day.

    Submitted after each live session (manually or via StreamYard webhook).
    Each phone in `attendees` gets a day{N}_live_joined ScoreEvent recorded,
    which unlocks the main (attended) template for the next day's broadcast.
    """
    edition_key: str
    day_number: int = Field(..., ge=1, le=3)  # 1, 2, or 3
    attendees: list[str]                       # international phone numbers


def _upsert_contact_score(db: Session, contact_id: str, points: int) -> None:
    """Add points to ContactScore and refresh Segment — mirrors scoring service logic."""
    from datetime import datetime, timezone

    contact_score = (
        db.query(ContactScore).filter(ContactScore.contact_id == contact_id).first()
    )
    if contact_score:
        contact_score.total_score += points
        contact_score.last_updated = datetime.now(timezone.utc)
    else:
        contact_score = ContactScore(
            contact_id=contact_id,
            total_score=points,
            last_updated=datetime.now(timezone.utc),
        )
        db.add(contact_score)

    db.flush()
    total = contact_score.total_score

    segment = (
        "froid" if total <= 15
        else "tiede" if total <= 40
        else "chaud" if total <= 75
        else "tres_chaud"
    )
    db.add(Segment(contact_id=contact_id, segment=segment, score=total))


@router.post("/streamyard/registrants", status_code=status.HTTP_202_ACCEPTED)
def streamyard_registrants(payload: RegistrantsPayload, db: Session = Depends(get_db)):
    """
    Record StreamYard event-page registrations for a challenge day (batch endpoint).

    Call this before or after the live session with the StreamYard registrant list.
    Each phone that registered (but may or may not have attended) gets a
    day{N}_streamyard_registered ScoreEvent (idempotent — skips duplicates).

    This feeds the MIDDLE branch of 3-way broadcast routing:
      (1) day{N}_live_joined              → attended → live_day{N}_attended
      (2) day{N}_streamyard_registered    → registered but absent → live_day{N}_registered_absent
      (3) neither                         → never registered → live_day{N}_not_registered

    Usage example:
      POST /webhooks/streamyard/registrants
      {
        "edition_key": "2026-05-07-eu",
        "day_number": 1,
        "registrants": ["33600000001", "33600000002"]
      }
    """
    event_type = f"day{payload.day_number}_streamyard_registered"
    points = SCORE_RULES.get(event_type, 0)

    recorded: list[str] = []
    already_recorded: list[str] = []
    not_found: list[str] = []

    for raw_phone in payload.registrants:
        phone = raw_phone.lstrip("+")
        contact = db.query(Contact).filter(Contact.phone == phone).first()
        if not contact:
            logger.warning("Registrants: contact not found for phone %s", phone)
            not_found.append(phone)
            continue

        existing = (
            db.query(ScoreEvent)
            .filter(
                ScoreEvent.contact_id == contact.id,
                ScoreEvent.event_type == event_type,
            )
            .first()
        )
        if existing:
            already_recorded.append(contact.id)
            continue

        db.add(ScoreEvent(
            contact_id=contact.id,
            event_type=event_type,
            points=points,
        ))
        _upsert_contact_score(db, contact.id, points)
        recorded.append(contact.id)
        logger.info(
            "StreamYard registration recorded: contact=%s event=%s points=%d",
            contact.id, event_type, points,
        )

    db.commit()

    return {
        "edition_key": payload.edition_key,
        "day_number": payload.day_number,
        "event_type": event_type,
        "recorded": len(recorded),
        "already_recorded": len(already_recorded),
        "not_found": len(not_found),
        "contact_ids": recorded,
    }


@router.post("/streamyard/attendance", status_code=status.HTTP_202_ACCEPTED)
def streamyard_attendance(payload: AttendancePayload, db: Session = Depends(get_db)):
    """
    Record live attendance for a challenge day (batch endpoint).

    For each phone number in `attendees`:
      - Looks up the Contact by phone.
      - Creates a ScoreEvent `day{N}_live_joined` (idempotent — skips duplicates).
      - Updates ContactScore running total + Segment.

    This unlocks the main (non-catchup) template for the next broadcast:
      day1_live_joined → challenge_day_2   (instead of challenge_day_2_catchup)
      day2_live_joined → challenge_day_3   (instead of challenge_day_3_catchup)
      day3_live_joined → post_challenge_recap (instead of post_challenge_missed)

    Usage example:
      POST /webhooks/streamyard/attendance
      {
        "edition_key": "2026-05-07-eu",
        "day_number": 1,
        "attendees": ["33600000001", "33600000002"]
      }
    """
    event_type = f"day{payload.day_number}_live_joined"
    points = SCORE_RULES.get(event_type, 0)

    recorded: list[str] = []
    already_recorded: list[str] = []
    not_found: list[str] = []

    for raw_phone in payload.attendees:
        # Normalise: strip leading '+'
        phone = raw_phone.lstrip("+")

        contact = db.query(Contact).filter(Contact.phone == phone).first()
        if not contact:
            logger.warning("Attendance: contact not found for phone %s", phone)
            not_found.append(phone)
            continue

        # Idempotency: skip if event already recorded for this contact
        existing = (
            db.query(ScoreEvent)
            .filter(
                ScoreEvent.contact_id == contact.id,
                ScoreEvent.event_type == event_type,
            )
            .first()
        )
        if existing:
            already_recorded.append(contact.id)
            continue

        db.add(ScoreEvent(
            contact_id=contact.id,
            event_type=event_type,
            points=points,
        ))
        _upsert_contact_score(db, contact.id, points)
        recorded.append(contact.id)
        logger.info(
            "Attendance recorded: contact=%s event=%s points=%d",
            contact.id, event_type, points,
        )

    db.commit()

    return {
        "edition_key": payload.edition_key,
        "day_number": payload.day_number,
        "event_type": event_type,
        "recorded": len(recorded),
        "already_recorded": len(already_recorded),
        "not_found": len(not_found),
        "contact_ids": recorded,
    }


app = FastAPI()
app.include_router(router)
