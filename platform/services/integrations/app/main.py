import logging
import os
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import httpx

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.db.models import AuditEvent, CampaignEnrollment, ChallengeEdition, Consent, Contact, ContactScore, InboundMessage, Message, ScoreEvent, Segment
from shared.db.session import get_db
from services.conversation_ai.app.service import build_reply
from services.integrations.app.normalizer import normalize_systemeio
from services.messaging.app.providers.mock import MockProvider
from services.messaging.app.providers.wati import WatiProvider
from services.scoring.app.rules import SCORE_RULES

logger = logging.getLogger(__name__)

# Only attempt to schedule Celery tasks when Redis is reachable (not in tests).
_CELERY_ENABLED = bool(os.getenv("REDIS_URL"))

router = APIRouter(prefix="/webhooks")
ops_router = APIRouter(prefix="/ops/streamyard")

_SCRIPT_ACKNOWLEDGEMENTS = {
    "ok",
    "okay",
    "ok merci",
    "merci",
    "d accord",
    "daccord",
    "cool",
    "super",
    "parfait",
    "tres bien",
    "oui",
    "oui ok",
    "d acc",
}

_SCRIPT_PRIORITIZED_INTENTS = {
    "default",
    "clarification_request",
    "acknowledgement_no_reply",
    "financial_objection",
    "objection_financial_soft",
    "objection_financial_strong",
    "product_choice_question",
    "time_objection",
}

_SAFE_UNKNOWN_CONTACT_INTENTS = {
    "faq_start_time",
    "faq_challenge_overview",
    "faq_whatsapp_group_join",
    "entry_choice_beginner",
    "entry_choice_started",
    "entry_choice_question",
    "soft_open_invitation",
}


def _canonical_phone(phone: str | None) -> str:
    return (phone or "").strip().lstrip("+")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_inbound_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _normalize_script_text(text: str | None) -> str:
    lowered = (text or "").strip().lower()
    ascii_text = (
        unicodedata.normalize("NFKD", lowered)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    ascii_text = re.sub(r"[^\w\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _same_reply_family(left: str | None, right: str | None) -> bool:
    left_norm = _normalize_script_text(left)
    right_norm = _normalize_script_text(right)
    if not left_norm or not right_norm:
        return False
    if left_norm == right_norm:
        return True
    repeated_families = [
        "n hesite pas si t as une question sur le challenge",
        "je veux bien t aider tu peux preciser",
    ]
    return any(family in left_norm and family in right_norm for family in repeated_families)


def _find_contact_by_phone(db: Session, phone: str | None) -> Contact | None:
    canonical = _canonical_phone(phone)
    if not canonical:
        return None
    return (
        db.query(Contact)
        .filter((Contact.phone == canonical) | (Contact.phone == f"+{canonical}"))
        .first()
    )


def _find_recent_duplicate_inbound(
    db: Session,
    *,
    phone: str | None,
    text: str,
    window_seconds: int = 180,
) -> InboundMessage | None:
    canonical = _canonical_phone(phone)
    if not canonical or not text.strip():
        return None

    cutoff = _utcnow() - timedelta(seconds=window_seconds)
    candidates = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.phone.in_([canonical, f"+{canonical}"]),
            InboundMessage.received_at >= cutoff,
        )
        .order_by(InboundMessage.received_at.desc())
        .all()
    )
    normalized = _normalize_inbound_text(text)
    for row in candidates:
        if _normalize_inbound_text(row.text) == normalized and (row.ai_reply or "").strip():
            return row
    return None


def _find_message_by_provider_id(db: Session, provider_message_id: str) -> Message | None:
    """Find the outbound audit message row linked to a Wati localMessageId.

    Falls back to Message.id for backward-compatibility with older rows/tests.
    """
    if not provider_message_id:
        return None
    row = (
        db.query(Message)
        .filter(Message.provider_message_id == provider_message_id)
        .first()
    )
    if row:
        return row
    return db.query(Message).filter(Message.id == provider_message_id).first()


def _latest_message_for_contact(db: Session, contact_id: str | None) -> Message | None:
    if not contact_id:
        return None
    return (
        db.query(Message)
        .filter(Message.contact_id == contact_id)
        .order_by(Message.created_at.desc())
        .first()
    )


def _latest_inbound_for_contact(db: Session, contact_id: str | None) -> InboundMessage | None:
    if not contact_id:
        return None
    return (
        db.query(InboundMessage)
        .filter(InboundMessage.contact_id == contact_id)
        .order_by(InboundMessage.received_at.desc())
        .first()
    )


def _latest_enrollment_for_contact(db: Session, contact_id: str | None) -> CampaignEnrollment | None:
    if not contact_id:
        return None
    return (
        db.query(CampaignEnrollment)
        .filter(CampaignEnrollment.contact_id == contact_id)
        .order_by(CampaignEnrollment.created_at.desc())
        .first()
    )


def _edition_links_summary(db: Session, edition_key: str | None) -> str:
    if not edition_key:
        return ""
    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )
    if not edition:
        return ""
    parts = []
    for label, value in [
        ("day1", edition.day1_url),
        ("day2", edition.day2_url),
        ("day3", edition.day3_url),
    ]:
        if value:
            parts.append(f"{label}={value}")
    return "; ".join(parts)


def _build_ai_context(db: Session, contact: Contact | None) -> dict:
    contact_id = contact.id if contact else None
    latest_outbound = _latest_message_for_contact(db, contact_id)
    latest_inbound = _latest_inbound_for_contact(db, contact_id)
    enrollment = _latest_enrollment_for_contact(db, contact_id)
    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == enrollment.edition_key)
        .first()
    ) if enrollment and enrollment.edition_key else None
    return {
        "contact_id": contact_id,
        "contact_first_name": contact.first_name if contact else "",
        "cohort": enrollment.cohort if enrollment else "",
        "edition_key": enrollment.edition_key if enrollment else "",
        "edition_date": edition.edition_date if edition else "",
        "current_step": enrollment.current_step if enrollment else "",
        "last_outbound_template": latest_outbound.template_key if latest_outbound else "",
        "last_outbound_status": latest_outbound.status if latest_outbound else "",
        "last_outbound_variables": latest_outbound.variables if latest_outbound else "",
        "last_ai_reply": latest_inbound.ai_reply if latest_inbound else "",
        "last_ai_intent": latest_inbound.intent if latest_inbound else "",
        "active_live_links": _edition_links_summary(db, enrollment.edition_key if enrollment else None),
    }


def _find_active_edition(db: Session, cohort: str) -> "ChallengeEdition | None":
    """Return the nearest active or upcoming ChallengeEdition for the given cohort.

    The window includes editions from J-7 (7 days in the future) down to J-6
    in the past (challenge started up to 6 days ago), so that late registrants
    who sign up on Day 2 or Day 3 of an ongoing challenge still get enrolled.

    The closest edition_date (ascending) is preferred so early registrants bind
    to the next edition rather than a very recent past one.
    """
    from datetime import date, timedelta
    today = date.today()
    # Include editions up to 6 days in the past so that contacts who register
    # on Day 2 or Day 3 of an ongoing challenge still get enrolled.
    window_start = (today - timedelta(days=6)).isoformat()
    return (
        db.query(ChallengeEdition)
        .filter(
            ChallengeEdition.cohort == cohort,
            ChallengeEdition.edition_date >= window_start,
        )
        .order_by(ChallengeEdition.edition_date.asc())
        .first()
    )


def _edition_date_from_key(edition_key: str) -> str:
    """Validate edition keys created from operator inputs.

    Expected format: YYYY-MM-DD-eu, YYYY-MM-DD-usca or YYYY-MM-DD-us-ca.
    This prevents accidental business titles from creating fake editions.
    """
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-(eu|usca|us-ca)", (edition_key or "").strip().lower())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="edition_key must use the format YYYY-MM-DD-eu or YYYY-MM-DD-usca.",
        )
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="edition_key starts with an invalid date.",
        ) from None
    return match.group(1)


def _get_or_create_edition(
    db: Session,
    *,
    edition_key: str,
    cohort: str,
    campaign_key: str = "challenge-amazon-fba",
) -> ChallengeEdition:
    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )
    if edition:
        return edition

    edition_date = _edition_date_from_key(edition_key)
    edition = ChallengeEdition(
        id=f"ed_{uuid4().hex[:8]}",
        campaign_key=campaign_key,
        edition_key=edition_key,
        cohort=cohort,
        edition_date=edition_date,
    )
    db.add(edition)
    db.commit()
    db.refresh(edition)
    return edition


def _get_provider():
    """Return WatiProvider when credentials are configured, else MockProvider."""
    if settings.wati_api_url and settings.wati_api_token:
        return WatiProvider(settings.wati_api_url, settings.wati_api_token)
    return MockProvider()


def _require_ops_token(
    x_ops_token: str | None = Header(default=None, alias="X-Ops-Token"),
    token: str | None = Query(default=None),
):
    expected = settings.ops_portal_token.strip()
    provided = (x_ops_token or token or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="OPS_PORTAL_TOKEN is not configured.")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid operator token.")
    return provided


def _has_sent_template(db: Session, contact_id: str, template_key: str) -> bool:
    return (
        db.query(Message)
        .filter(Message.contact_id == contact_id, Message.template_key == template_key)
        .first()
        is not None
    )


def _compute_post_welcome_step(days_until_challenge: int) -> str:
    """Return the next broadcast step after the immediate welcome is sent."""
    if days_until_challenge <= 0:
        return "DAY_1"
    if days_until_challenge >= 6:
        return "COUNTDOWN_J6"
    return f"COUNTDOWN_J{days_until_challenge}"


def _send_welcome_message(db: Session, contact: Contact) -> dict:
    """Send the immediate welcome template and persist its audit row."""
    provider = _get_provider()
    variables = {
        "1": (contact.first_name or "").strip() or "vous",
        "script_state": {
            "flow": "entry_questionnaire",
            "stage": "awaiting_choice",
            "rephrase_count": 0,
        },
    }
    result = provider.send_template(contact.phone, "welcome", {"1": variables["1"]})
    row = Message(
        id=f"msg_{uuid4().hex[:8]}",
        contact_id=contact.id,
        template_key="welcome",
        variables=variables,
        provider_message_id=result.get("provider_message_id"),
        status=result.get("status", "queued"),
        provider=result.get("provider", "mock"),
    )
    db.add(row)
    db.commit()
    return {
        "message_id": row.id,
        "status": row.status,
        "provider": row.provider,
        "provider_message_id": row.provider_message_id,
    }


def _send_ai_session_reply(
    db: Session,
    phone: str,
    contact_id: str | None,
    reply_text: str,
    *,
    script_state: dict | None = None,
) -> dict:
    """Send an AI-generated WhatsApp session reply and persist an audit row when possible."""
    provider = _get_provider()
    result = provider.send_text(phone, reply_text)

    message_id = None
    if contact_id:
        variables = {"text": reply_text}
        if script_state:
            variables["script_state"] = script_state
        row = Message(
            id=f"msg_{uuid4().hex[:8]}",
            contact_id=contact_id,
            template_key="ai_session_reply",
            variables=variables,
            provider_message_id=result.get("provider_message_id"),
            status=result.get("status", "queued"),
            provider=result.get("provider", "mock"),
        )
        db.add(row)
        db.commit()
        message_id = row.id

    return {
        "message_id": message_id,
        "status": result.get("status", "queued"),
        "provider": result.get("provider", "mock"),
        "provider_message_id": result.get("provider_message_id"),
        "error": result.get("error"),
    }


def _no_auto_reply_delivery(status: str = "awaiting_human") -> dict:
    return {
        "message_id": None,
        "status": status,
        "provider": "wati",
        "provider_message_id": None,
        "error": None,
    }


def _is_script_acknowledgement(normalized_text: str) -> bool:
    return normalized_text in _SCRIPT_ACKNOWLEDGEMENTS


def _capture_interest_followup_reply(topic: str | None) -> dict:
    if topic == "availability":
        return {
            "reply": "Merci, c'est bien note. Vous recevrez le lien avant chaque session pour vous organiser simplement.",
            "needs_human": False,
            "intent": "interest_followup_availability_captured",
        }
    if topic == "obstacle":
        return {
            "reply": "Merci, c'est bien note. Le challenge va justement vous aider a lever ce frein de facon concrete.",
            "needs_human": False,
            "intent": "interest_followup_obstacle_captured",
        }
    return {
        "reply": "Merci, c'est bien note. Le challenge va justement vous aider a clarifier cet objectif de facon concrete.",
        "needs_human": False,
        "intent": "interest_followup_objective_captured",
    }


def _entry_questionnaire_rephrase() -> dict:
    return {
        "reply": "Reponds juste avec 1, 2 ou 3 pour que je te reponde correctement.",
        "needs_human": False,
        "intent": "entry_questionnaire_rephrase",
        "script_state": {
            "flow": "entry_questionnaire",
            "stage": "rephrased_once",
            "rephrase_count": 1,
        },
    }


def _entry_questionnaire_escalation() -> dict:
    return {
        "reply": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
        "needs_human": True,
        "intent": "human_escalation",
        "send_reply": False,
    }


def _entry_questionnaire_reply(latest_outbound: Message, result: dict) -> dict | None:
    variables = latest_outbound.variables or {}
    script_state = variables.get("script_state")
    if not isinstance(script_state, dict):
        return None
    if script_state.get("flow") != "entry_questionnaire":
        return None

    if script_state.get("stage") == "choice_captured":
        return result

    current_intent = result.get("intent", "default")
    if current_intent.startswith("faq_") or current_intent in {
        "human_escalation",
        "payment_failure_followup_needed",
        "installment_plan_request",
        "skeptic_trust_objection",
        "financial_objection",
        "objection_financial_soft",
        "objection_financial_strong",
        "geo_constraint_question",
        "entry_choice_question",
    }:
        return result

    if current_intent in {"entry_choice_beginner", "entry_choice_started"}:
        return result

    if script_state.get("rephrase_count", 0) == 0:
        return _entry_questionnaire_rephrase()

    return _entry_questionnaire_escalation()


def _scripted_conversation_reply(latest_outbound: Message, incoming_text: str, result: dict) -> dict | None:
    variables = latest_outbound.variables or {}
    script_state = variables.get("script_state")
    if not isinstance(script_state, dict):
        return None
    if script_state.get("flow") == "entry_questionnaire":
        return None

    current_intent = result.get("intent", "default")
    if current_intent.startswith("faq_") or current_intent in {
        "human_escalation",
        "payment_failure_followup_needed",
        "installment_plan_request",
        "skeptic_trust_objection",
        "financial_objection",
        "objection_financial_soft",
        "objection_financial_strong",
        "geo_constraint_question",
    }:
        return None

    if script_state.get("next_stage") != "awaiting_interest_followup":
        return None

    normalized = _normalize_script_text(incoming_text)
    if _is_script_acknowledgement(normalized):
        return {
            "reply": "N'hesite pas si t'as une question sur le challenge 😊",
            "needs_human": False,
            "intent": "soft_open_invitation",
        }

    if current_intent in {"default", "clarification_request", "restricted_beginner_profile", "restricted_started_profile", "restricted_main_obstacle", "restricted_product_choice"}:
        return _capture_interest_followup_reply(script_state.get("topic"))

    return None

def _contextual_default_reply(
    db: Session,
    contact_id: str | None,
    incoming_text: str,
    result: dict,
) -> dict:
    """Use the latest outbound AI reply as minimal state for one follow-up capture."""
    if not contact_id:
        return result

    latest_outbound = (
        db.query(Message)
        .filter(Message.contact_id == contact_id)
        .order_by(Message.created_at.desc())
        .first()
    )
    if not latest_outbound or latest_outbound.template_key not in {"ai_session_reply", "welcome"}:
        return result

    questionnaire = _entry_questionnaire_reply(latest_outbound, result)
    if questionnaire:
        return questionnaire

    scripted = _scripted_conversation_reply(latest_outbound, incoming_text, result)
    if scripted:
        return scripted

    return result


def _prevent_repetitive_reply(db: Session, contact_id: str | None, result: dict) -> dict:
    """Avoid sending the same generic bot line again and again."""
    latest_inbound = _latest_inbound_for_contact(db, contact_id)
    if not latest_inbound:
        return result

    reply = result.get("reply") or ""
    if not _same_reply_family(latest_inbound.ai_reply, reply):
        return result

    updated = dict(result)
    if result.get("intent") == "clarification_request":
        updated["needs_human"] = True
        updated["send_reply"] = False
        updated["intent"] = "repeated_clarification_escalated"
        return updated

    updated["reply"] = ""
    updated["send_reply"] = False
    updated["intent"] = "acknowledgement_no_reply"
    updated["needs_human"] = False
    return updated


def process_inbound_wati_message(db: Session, phone: str, text: str) -> dict:
    """Process one inbound WhatsApp message and send the AI/session reply."""
    contact = _find_contact_by_phone(db, phone)
    contact_id = contact.id if contact else None

    duplicate = _find_recent_duplicate_inbound(db, phone=phone, text=text)
    if duplicate:
        return {
            "id": duplicate.id,
            "phone": phone,
            "contact_id": duplicate.contact_id,
            "reply": duplicate.ai_reply or "",
            "needs_human": duplicate.needs_human,
            "intent": duplicate.intent,
            "delivery": _no_auto_reply_delivery("duplicate_ignored"),
        }

    if not settings.whatsapp_auto_reply_enabled:
        inbound = InboundMessage(
            phone=phone,
            contact_id=contact_id,
            text=text,
            ai_reply="",
            needs_human=True,
            intent="auto_reply_disabled",
        )
        db.add(inbound)
        if contact_id and _looks_like_question(text):
            _record_score_event(db, contact_id, "asked_question")
        db.commit()
        db.refresh(inbound)
        return {
            "id": inbound.id,
            "phone": phone,
            "contact_id": contact_id,
            "reply": "",
            "needs_human": True,
            "intent": "auto_reply_disabled",
            "delivery": _no_auto_reply_delivery("auto_reply_disabled"),
        }

    ai_context = _build_ai_context(db, contact)
    result = build_reply(text, context=ai_context)
    result = _contextual_default_reply(db, contact_id, text, result)
    result = _prevent_repetitive_reply(db, contact_id, result)
    message_is_question = _looks_like_question(text)

    # Unknown contact or broad unknown question -> do not improvise a bot reply.
    if (
        (not contact_id and result.get("intent") not in _SAFE_UNKNOWN_CONTACT_INTENTS)
        or (
        result.get("intent") == "clarification_request" and message_is_question
        )
    ):
        result["needs_human"] = True
        result["send_reply"] = False

    inbound = InboundMessage(
        phone=phone,
        contact_id=contact_id,
        text=text,
        ai_reply=result["reply"],
        needs_human=result.get("needs_human", False),
        intent=result.get("intent", "default"),
    )
    db.add(inbound)
    if contact_id:
        _record_score_event(db, contact_id, "replied_message")
        if _looks_like_question(text):
            _record_score_event(db, contact_id, "asked_question")
    db.commit()
    db.refresh(inbound)

    should_send_reply = bool((result.get("reply") or "").strip()) and result.get("send_reply", True)
    delivery = (
        _send_ai_session_reply(
            db,
            phone,
            contact_id,
            result["reply"],
            script_state=result.get("script_state"),
        )
        if should_send_reply
        else _no_auto_reply_delivery(
            "awaiting_human" if result.get("needs_human") else "no_auto_reply"
        )
    )

    try:
        from services.notifications.app.email import notify_closer, should_notify_closer
        if should_notify_closer(result.get("intent", ""), result.get("needs_human", False)):
            contact_score = (
                db.query(ContactScore)
                .filter(ContactScore.contact_id == contact_id)
                .first()
            ) if contact_id else None
            score = contact_score.total_score if contact_score else 0
            notify_closer(
                phone=phone,
                contact_id=contact_id,
                message_text=text,
                ai_reply=result["reply"],
                intent=result.get("intent", "default"),
                score=score,
            )
    except Exception as exc:
        logger.error("Closer notification error (non-blocking): %s", exc)

    return {
        "id": inbound.id,
        "phone": phone,
        "contact_id": contact_id,
        "reply": result["reply"],
        "needs_human": result["needs_human"],
        "intent": result["intent"],
        "delivery": delivery,
    }


def _auto_enroll(db: Session, contact_id: str, cohort: str) -> dict | None:
    """Enroll a newly registered contact in the active edition at the right step.

    Calculates days_until_challenge from the active edition's date and calls
    compute_start_step() to skip past already-elapsed countdown steps.
    Returns enrollment descriptor or None if no active edition found.
    """
    from datetime import date
    from shared.db.models import CampaignEnrollment

    edition = _find_active_edition(db, cohort)
    if not edition:
        logger.warning("Auto-enroll: no active edition found for cohort=%s", cohort)
        return None

    # Avoid duplicate enrollments for the same contact+edition
    existing_enrollment = (
        db.query(CampaignEnrollment)
        .filter(
            CampaignEnrollment.contact_id == contact_id,
            CampaignEnrollment.edition_key == edition.edition_key,
        )
        .first()
    )
    if existing_enrollment:
        logger.info(
            "Auto-enroll: contact=%s already enrolled in edition=%s",
            contact_id, edition.edition_key,
        )
        return None

    edition_date = date.fromisoformat(edition.edition_date)
    days_until = (edition_date - date.today()).days
    start_step = _compute_post_welcome_step(days_until)

    enrollment = CampaignEnrollment(
        id=f"enr_{uuid4().hex[:8]}",
        contact_id=contact_id,
        campaign_key=edition.campaign_key,
        edition_key=edition.edition_key,
        current_step=start_step,
        cohort=cohort,
    )
    db.add(enrollment)
    db.commit()

    logger.info(
        "Auto-enrolled: contact=%s edition=%s cohort=%s step=%s days_until=%d",
        contact_id, edition.edition_key, cohort, start_step, days_until,
    )
    return {
        "edition_key": edition.edition_key,
        "cohort": cohort,
        "start_step": start_step,
        "days_until_challenge": days_until,
    }


@router.post("/systemeio", status_code=status.HTTP_202_ACCEPTED)
def systemeio_webhook(payload: dict, db: Session = Depends(get_db)):
    """
    Receive Systeme.io webhook, normalize, upsert contact, record opt-in consent,
    and auto-enroll the contact in the active edition at the correct journey step.

    Cohort detection:
      - Payload may include a top-level "cohort" field set in Systeme.io automation
        (e.g. "EU" or "US-CA"). Defaults to "EU" if absent.
      - Configure two separate Systeme.io automations (one per list) and add
        {"cohort": "EU"} or {"cohort": "US-CA"} to each webhook payload.
    """
    normalized = normalize_systemeio(payload)
    lead = normalized["payload"]
    phone = lead.get("phone")
    # Cohort from payload top-level field (set in Systeme.io automation)
    cohort = payload.get("cohort", "EU").upper()
    contact_id = None
    enrollment_info = None
    welcome_info = None

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

        # Auto-enroll in the active edition at the correct journey step
        enrollment_info = _auto_enroll(db, contact_id, cohort)

        # Immediate welcome message on first qualifying registration.
        if contact_id and not _has_sent_template(db, contact_id, "welcome"):
            target_contact = db.query(Contact).filter(Contact.id == contact_id).first()
            if target_contact:
                welcome_info = _send_welcome_message(db, target_contact)

    return {
        **normalized,
        "contact_id": contact_id,
        "enrollment": enrollment_info,
        "welcome": welcome_info,
    }


@router.post("/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(
    payload: dict,
    db: Session = Depends(get_db),
    require_scheduler: bool = False,
):
    """
    Register or update a StreamYard session for a challenge edition.
    The StreamYard join_url changes at every edition â€” this stores it so
    the messaging service can inject the right link in Day-1/2/3 messages.
    """
    edition_key = payload.get("edition_key", "")
    edition_date = _edition_date_from_key(edition_key)
    cohort = payload.get("region", "EU")
    join_url = payload.get("join_url")
    campaign_key = payload.get("challenge_key", "challenge-amazon-fba")

    day_number = payload.get("day_number")  # optional: 1, 2 or 3

    if require_scheduler and not _CELERY_ENABLED:
        raise HTTPException(
            status_code=503,
            detail=(
                "Rappels live non programmés : le broker Celery/Redis n'est pas "
                "disponible pour cette API."
            ),
        )

    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )
    if edition:
        if join_url:
            if day_number == 1:
                edition.day1_url = join_url
            elif day_number == 2:
                edition.day2_url = join_url
            elif day_number == 3:
                edition.day3_url = join_url
            else:
                edition.streamyard_url = join_url  # fallback / backward compat
        db.commit()
    else:
        edition = ChallengeEdition(
            id=f"ed_{uuid4().hex[:8]}",
            campaign_key=campaign_key,
            edition_key=edition_key,
            cohort=cohort,
            edition_date=edition_date,
        )
        db.add(edition)
        if day_number == 1:
            edition.day1_url = join_url
        elif day_number == 2:
            edition.day2_url = join_url
        elif day_number == 3:
            edition.day3_url = join_url
        else:
            edition.streamyard_url = join_url
        db.commit()

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
                day_number=day_number,
            )
            scheduled_count = len(scheduled)
        except Exception as exc:
            logger.error("Failed to schedule tasks for edition %s: %s", edition_key, exc)
            if require_scheduler:
                raise HTTPException(
                    status_code=503,
                    detail=f"Rappels live non programmés : {exc}",
                ) from exc

    if require_scheduler and scheduled_count == 0:
        raise HTTPException(
            status_code=503,
            detail=(
                "Rappels live non programmés : aucune tâche future n'a été créée. "
                "Vérifie la date, le jour choisi et l'heure du live."
            ),
        )

    return {
        "challenge_key": campaign_key,
        "edition_key": edition_key,
        "region": cohort,
        "join_url": join_url,
        "day_number": day_number,
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
            "day1_url": e.day1_url,
            "day2_url": e.day2_url,
            "day3_url": e.day3_url,
            "payment_url": e.payment_url,
            "closer_booking_url": e.closer_booking_url,
            "replay_day1_url": e.replay_day1_url,
            "replay_day2_url": e.replay_day2_url,
            "replay_day3_url": e.replay_day3_url,
        }
        for e in editions
    ]


@router.post("/wati", status_code=status.HTTP_200_OK)
def wati_inbound(payload: dict, db: Session = Depends(get_db)):
    """
    Receive a Wati webhook event. Wati sends ALL event types to the same URL.

    Handled event types (Context7 / Wati docs):
      messageReceived           â€” inbound message â†’ AI reply + persist
      sentMessageDELIVERED_v2   â€” delivery confirmation â†’ acknowledge
      sentMessageREAD_v2        â€” read receipt â†’ record opened_message score
      templateMessageFailed     â€” template send failure â†’ log warning

    Wati v3 payload for messageReceived:
        {"waId": "336...", "text": "...", "eventType": "messageReceived", ...}
    Legacy format (some integrations):
        {"waId": "336...", "text": {"body": "..."}}
    """
    event_type = payload.get("eventType") or payload.get("type") or "messageReceived"

    # â”€â”€ Delivery confirmation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if event_type == "sentMessageDELIVERED_v2":
        local_msg_id = payload.get("localMessageId", "")
        msg_row = _find_message_by_provider_id(db, local_msg_id)
        if msg_row:
            msg_row.status = "delivered"
            db.commit()
        return {"status": "acknowledged", "eventType": event_type}

    # â”€â”€ Read receipt â†’ record opened_message score event â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if event_type == "sentMessageREAD_v2":
        local_msg_id = payload.get("localMessageId", "")
        if local_msg_id:
            msg_row = _find_message_by_provider_id(db, local_msg_id)
            if msg_row and msg_row.contact_id:
                msg_row.status = "read"
                _record_score_event(db, msg_row.contact_id, "opened_message")
                db.commit()
        return {"status": "acknowledged", "eventType": event_type}

    # â”€â”€ Template send failure â†’ log warning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Inbound message (messageReceived / legacy) â†’ AI reply â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    return process_inbound_wati_message(db, phone, text)


def _intent_priority(intent: str) -> str:
    """
    Map a classified intent to an operator priority level.
    Spec Â§4 escalation rules:
      haute    â€” payment failure, installment request, explicit human call
      moyenne  â€” sceptic/trust objection, strong financial, persistent email issue
      faible   â€” simple FAQ, next challenge request, generic financial
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


# â”€â”€ Attendance tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class RegistrantsPayload(BaseModel):
    """Batch StreamYard registration report for one challenge day.

    Submitted before or after a live session with the list of phones that
    registered on the StreamYard event page (regardless of actual attendance).
    Each phone gets a day{N}_streamyard_registered ScoreEvent (idempotent).

    This creates the MIDDLE branch of 3-way routing:
      day{N}_live_joined          â†’ live_day{N}_attended
      day{N}_streamyard_registered (no live_joined) â†’ live_day{N}_registered_absent
      neither                     â†’ live_day{N}_not_registered
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


class StreamYardSessionUpdatePayload(BaseModel):
    challenge_key: str = "challenge-amazon-fba"
    edition_key: str
    region: str
    day_number: int = Field(..., ge=1, le=3)
    join_url: str


class StreamYardEditionResourcesPayload(BaseModel):
    challenge_key: str = "challenge-amazon-fba"
    edition_key: str
    region: str
    payment_url: str | None = None
    closer_booking_url: str | None = None
    replay_day1_url: str | None = None
    replay_day2_url: str | None = None
    replay_day3_url: str | None = None


def _upsert_contact_score(db: Session, contact_id: str, points: int) -> None:
    """Add points to ContactScore and refresh Segment â€” mirrors scoring service logic."""
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


def _record_score_event(db: Session, contact_id: str, event_type: str) -> dict:
    """Persist one engagement event and return the resulting score snapshot."""
    points = SCORE_RULES[event_type]
    db.add(ScoreEvent(
        contact_id=contact_id,
        event_type=event_type,
        points=points,
    ))
    _upsert_contact_score(db, contact_id, points)
    db.flush()
    contact_score = (
        db.query(ContactScore)
        .filter(ContactScore.contact_id == contact_id)
        .first()
    )
    total_score = contact_score.total_score if contact_score else points
    segment = (
        "froid" if total_score <= 15
        else "tiede" if total_score <= 40
        else "chaud" if total_score <= 75
        else "tres_chaud"
    )
    return {
        "points": points,
        "total_score": total_score,
        "segment": segment,
    }


def _looks_like_question(text: str) -> bool:
    """Keep question scoring conservative so short acknowledgements do not inflate scores."""
    normalized = text.strip().lower()
    if "?" in normalized:
        return True
    return normalized.startswith((
        "comment ",
        "pourquoi ",
        "quand ",
        "quel ",
        "quelle ",
        "quels ",
        "quelles ",
        "combien ",
        "est-ce ",
        "est ce ",
        "ou ",
        "oÃ¹ ",
    ))


_ENGAGEMENT_EVENT_ALIASES = {
    "group_joined": "group_whatsapp_joined",
    "whatsapp_group_joined": "group_whatsapp_joined",
    "streamyard_clicked": "streamyard_link_clicked",
    "streamyard_link_opened": "streamyard_link_clicked",
    "message_clicked": "clicked_link",
}


class EngagementPayload(BaseModel):
    event_type: str
    contact_id: str | None = None
    phone: str | None = None


@router.post("/engagement", status_code=status.HTTP_202_ACCEPTED)
def engagement_webhook(payload: EngagementPayload, db: Session = Depends(get_db)):
    """
    Record behavior signals coming from n8n, WawPlus, tracking redirects, or similar tools.
    Accepts either a contact_id or a phone number to keep external integration simple.
    """
    event_type = _ENGAGEMENT_EVENT_ALIASES.get(payload.event_type, payload.event_type)
    if event_type not in SCORE_RULES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event_type '{payload.event_type}'",
        )

    contact = None
    if payload.contact_id:
        contact = db.query(Contact).filter(Contact.id == payload.contact_id).first()
    elif payload.phone:
        phone = payload.phone.lstrip("+")
        contact = (
            db.query(Contact)
            .filter((Contact.phone == payload.phone) | (Contact.phone == phone))
            .first()
        )

    if not contact:
        return {"status": "ignored", "reason": "contact_not_found"}

    score_snapshot = _record_score_event(db, contact.id, event_type)
    db.commit()
    return {
        "status": "recorded",
        "contact_id": contact.id,
        "event_type": event_type,
        **score_snapshot,
    }


@router.post("/streamyard/registrants", status_code=status.HTTP_202_ACCEPTED)
def streamyard_registrants(payload: RegistrantsPayload, db: Session = Depends(get_db)):
    """
    Record StreamYard event-page registrations for a challenge day (batch endpoint).

    Call this before or after the live session with the StreamYard registrant list.
    Each phone that registered (but may or may not have attended) gets a
    day{N}_streamyard_registered ScoreEvent (idempotent â€” skips duplicates).

    This feeds the MIDDLE branch of 3-way broadcast routing:
      (1) day{N}_live_joined              â†’ attended â†’ live_day{N}_attended
      (2) day{N}_streamyard_registered    â†’ registered but absent â†’ live_day{N}_registered_absent
      (3) neither                         â†’ never registered â†’ live_day{N}_not_registered

    Usage example:
      POST /webhooks/streamyard/registrants
      {
        "edition_key": "2026-05-07-eu",
        "day_number": 1,
        "registrants": ["33600000001", "33600000002"]
      }
    """
    _edition_date_from_key(payload.edition_key)
    event_type = f"day{payload.day_number}_streamyard_registered"
    points = SCORE_RULES.get(event_type, 0)

    recorded: list[str] = []
    already_recorded: list[str] = []
    not_found: list[str] = []

    for raw_phone in payload.registrants:
        phone = raw_phone.lstrip("+")
        contact = _find_contact_by_phone(db, phone)
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
      - Creates a ScoreEvent `day{N}_live_joined` (idempotent â€” skips duplicates).
      - Updates ContactScore running total + Segment.

    This unlocks the main (non-catchup) template for the next broadcast:
      day1_live_joined â†’ challenge_day_2   (instead of challenge_day_2_catchup)
      day2_live_joined â†’ challenge_day_3   (instead of challenge_day_3_catchup)
      day3_live_joined â†’ post_challenge_recap (instead of post_challenge_missed)

    Usage example:
      POST /webhooks/streamyard/attendance
      {
        "edition_key": "2026-05-07-eu",
        "day_number": 1,
        "attendees": ["33600000001", "33600000002"]
      }
    """
    _edition_date_from_key(payload.edition_key)
    event_type = f"day{payload.day_number}_live_joined"
    points = SCORE_RULES.get(event_type, 0)

    recorded: list[str] = []
    already_recorded: list[str] = []
    not_found: list[str] = []

    for raw_phone in payload.attendees:
        # Normalise: strip leading '+'
        phone = raw_phone.lstrip("+")

        contact = _find_contact_by_phone(db, phone)
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


@ops_router.post("/session", status_code=status.HTTP_202_ACCEPTED)
def ops_streamyard_session(
    payload: StreamYardSessionUpdatePayload,
    _: str = Depends(_require_ops_token),
    db: Session = Depends(get_db),
):
    return streamyard_session(payload.model_dump(), db, require_scheduler=True)


@ops_router.post("/resources", status_code=status.HTTP_202_ACCEPTED)
def ops_streamyard_resources(
    payload: StreamYardEditionResourcesPayload,
    _: str = Depends(_require_ops_token),
    db: Session = Depends(get_db),
):
    edition = _get_or_create_edition(
        db,
        edition_key=payload.edition_key,
        cohort=payload.region,
        campaign_key=payload.challenge_key,
    )
    edition.payment_url = payload.payment_url or None
    edition.closer_booking_url = payload.closer_booking_url or None
    edition.replay_day1_url = payload.replay_day1_url or None
    edition.replay_day2_url = payload.replay_day2_url or None
    edition.replay_day3_url = payload.replay_day3_url or None
    db.commit()
    db.refresh(edition)
    return {
        "edition_key": edition.edition_key,
        "region": edition.cohort,
        "stored": True,
        "resources": {
            "payment_url": edition.payment_url,
            "closer_booking_url": edition.closer_booking_url,
            "replay_day1_url": edition.replay_day1_url,
            "replay_day2_url": edition.replay_day2_url,
            "replay_day3_url": edition.replay_day3_url,
        },
    }


@ops_router.post("/registrants", status_code=status.HTTP_202_ACCEPTED)
def ops_streamyard_registrants(
    payload: RegistrantsPayload,
    _: str = Depends(_require_ops_token),
    db: Session = Depends(get_db),
):
    return streamyard_registrants(payload, db)


@ops_router.post("/attendance", status_code=status.HTTP_202_ACCEPTED)
def ops_streamyard_attendance(
    payload: AttendancePayload,
    _: str = Depends(_require_ops_token),
    db: Session = Depends(get_db),
):
    return streamyard_attendance(payload, db)


@ops_router.get("/edition/{edition_key}")
def ops_get_edition_state(
    edition_key: str,
    _: str = Depends(_require_ops_token),
    db: Session = Depends(get_db),
):
    """Return the current state of a challenge edition for the OPS dashboard.

    Used by the StreamyardOpsPage to pre-fill fields and show what has already
    been sent — so operators can verify data before each live session.
    """
    from services.campaigns.app.challenge_calendar import get_cohort_config
    from zoneinfo import ZoneInfo

    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )
    if not edition:
        return {"found": False, "edition_key": edition_key}

    # ── Enrollment count ──────────────────────────────────────────────────────
    enrollment_count = (
        db.query(CampaignEnrollment)
        .filter(CampaignEnrollment.edition_key == edition_key)
        .count()
    )

    # ── Broadcast audit records ───────────────────────────────────────────────
    broadcast_audits = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.name == "campaign_daily_broadcast",
            AuditEvent.aggregate_id.startswith(edition_key + ":"),
        )
        .all()
    )
    broadcasts_done = [a.aggregate_id.split(":", 1)[-1] for a in broadcast_audits]

    # ── Timed reminder audit records ──────────────────────────────────────────
    reminder_audits = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.name == "timed_reminder",
            AuditEvent.aggregate_id.startswith(edition_key + ":"),
        )
        .all()
    )
    # format: "{edition_key}:day{N}:{timing}" → "day{N}:{timing}"
    reminders_done = [
        ":".join(a.aggregate_id.split(":")[1:]) for a in reminder_audits
    ]

    # ── Per-day attendance/registrant stats ───────────────────────────────────
    # Collect contact_ids enrolled in this edition for scoping
    enrolled_ids = [
        row.contact_id
        for row in db.query(CampaignEnrollment.contact_id)
        .filter(CampaignEnrollment.edition_key == edition_key)
        .all()
    ]

    day_stats: dict[str, dict] = {}
    for day in [1, 2, 3]:
        registered = attended = 0
        if enrolled_ids:
            registered = (
                db.query(ScoreEvent)
                .filter(
                    ScoreEvent.event_type == f"day{day}_streamyard_registered",
                    ScoreEvent.contact_id.in_(enrolled_ids),
                )
                .count()
            )
            attended = (
                db.query(ScoreEvent)
                .filter(
                    ScoreEvent.event_type == f"day{day}_live_joined",
                    ScoreEvent.contact_id.in_(enrolled_ids),
                )
                .count()
            )
        day_stats[f"day{day}"] = {"registered": registered, "attended": attended}

    # ── Compute schedule times in cohort local time ───────────────────────────
    cohort_cfg = get_cohort_config(edition.cohort)
    tz = ZoneInfo(cohort_cfg["timezone"])
    live_time = cohort_cfg["live_time"]
    broadcast_time = cohort_cfg.get("broadcast_time", "09:00")
    live_h, live_m = (int(x) for x in live_time.split(":"))

    from datetime import datetime as _dt, timedelta as _td
    schedule: list[dict] = []
    try:
        start_date = date.fromisoformat(edition.edition_date)
        for day in [1, 2, 3]:
            live_date = start_date + _td(days=day - 1)
            live_local = _dt(live_date.year, live_date.month, live_date.day,
                             live_h, live_m, tzinfo=tz)
            bcast_h, bcast_m = (int(x) for x in broadcast_time.split(":"))
            bcast_local = _dt(live_date.year, live_date.month, live_date.day,
                              bcast_h, bcast_m, tzinfo=tz)

            day_key = f"day{day}"
            broadcast_done = any(b == live_date.isoformat() for b in broadcasts_done)
            h10_done = f"{day_key}:h10" in reminders_done
            hplus5_done = f"{day_key}:h_plus_5" in reminders_done
            hplus2_done = f"{day_key}:h_plus_2" in reminders_done

            day_sched: dict = {
                "day": day,
                "date": live_date.isoformat(),
                "broadcast": {
                    "time_local": bcast_local.strftime("%Y-%m-%d %H:%M"),
                    "done": broadcast_done,
                    "templates": _broadcast_templates_for_day(day),
                },
                "h10": {
                    "time_local": (live_local - _td(minutes=10)).strftime("%Y-%m-%d %H:%M"),
                    "done": h10_done,
                    "template": f"live_day{day}_h10",
                },
                "hplus5": {
                    "time_local": (live_local + _td(minutes=5)).strftime("%Y-%m-%d %H:%M"),
                    "done": hplus5_done,
                    "template": f"live_day{day}_hplus5",
                },
            }
            if day == 3:
                day_sched["hplus2"] = {
                    "time_local": (live_local + _td(hours=2)).strftime("%Y-%m-%d %H:%M"),
                    "done": hplus2_done,
                    "template": "live_day3_offer_hplus2",
                }
            schedule.append(day_sched)
    except Exception:
        pass  # schedule is best-effort; don't crash the GET

    return {
        "found": True,
        "edition_key": edition.edition_key,
        "edition_date": edition.edition_date,
        "cohort": edition.cohort,
        "campaign_key": edition.campaign_key,
        "timezone": cohort_cfg["timezone"],
        "live_time": live_time,
        "enrollment_count": enrollment_count,
        "urls": {
            "day1_url": edition.day1_url or "",
            "day2_url": edition.day2_url or "",
            "day3_url": edition.day3_url or "",
            "streamyard_url": edition.streamyard_url or "",
            "payment_url": edition.payment_url or "",
            "closer_booking_url": edition.closer_booking_url or "",
            "replay_day1_url": edition.replay_day1_url or "",
            "replay_day2_url": edition.replay_day2_url or "",
            "replay_day3_url": edition.replay_day3_url or "",
        },
        "broadcasts_done": broadcasts_done,
        "reminders_done": reminders_done,
        "day_stats": day_stats,
        "schedule": schedule,
    }


# ── Bot admin proxy ───────────────────────────────────────────────────────────
# The bot is a separate FastAPI service (port 8001). These endpoints proxy the
# bot admin API through the ops_router so the OPS page doesn't need to know
# the bot's address and CORS is handled by the platform.

_BOT_BASE_URL = os.getenv("BOT_URL", "http://localhost:8001")
_BOT_API_KEY  = os.getenv("BOT_API_KEY", "")


def _bot_headers() -> dict:
    return {"X-Bot-Key": _BOT_API_KEY} if _BOT_API_KEY else {}


@ops_router.get("/bot/status")
def ops_bot_status(_: str = Depends(_require_ops_token)):
    """Return bot health + auto-reply state + 24h stats."""
    try:
        with httpx.Client(timeout=5) as client:
            health_r = client.get(f"{_BOT_BASE_URL}/health")
            health = health_r.json() if health_r.status_code == 200 else {}

            stats: dict = {}
            if _BOT_API_KEY:
                stats_r = client.get(
                    f"{_BOT_BASE_URL}/admin/stats",
                    headers=_bot_headers(),
                )
                if stats_r.status_code == 200:
                    stats = stats_r.json()

        return {
            "reachable": True,
            "auto_reply": health.get("auto_reply", False),
            "model": health.get("claude_model") or health.get("openai_model", "?"),
            "db_ok": health.get("db", False),
            "stats": stats,
        }
    except Exception as exc:
        logger.warning("Bot status check failed: %s", exc)
        return {"reachable": False, "auto_reply": False, "model": "?", "db_ok": False, "stats": {}}


class BotTogglePayload(BaseModel):
    enabled: bool


@ops_router.post("/bot/toggle")
def ops_bot_toggle(payload: BotTogglePayload, _: str = Depends(_require_ops_token)):
    """Enable or disable the bot auto-reply."""
    try:
        with httpx.Client(timeout=5) as client:
            r = client.post(
                f"{_BOT_BASE_URL}/admin/auto-reply/toggle",
                params={"enabled": payload.enabled},
                headers=_bot_headers(),
            )
        if r.status_code == 200:
            return {"ok": True, "auto_reply_enabled": r.json().get("auto_reply_enabled", payload.enabled)}
        return {"ok": False, "error": f"Bot returned {r.status_code}"}
    except Exception as exc:
        logger.error("Bot toggle failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Bot unreachable: {exc}")


class BotTestPayload(BaseModel):
    message: str
    phone: str = "33600000000"


@ops_router.post("/bot/test")
def ops_bot_test(payload: BotTestPayload, _: str = Depends(_require_ops_token)):
    """Simulate a message through the bot engine and return the response.

    Does NOT send anything to Wati — read-only simulation for the test console.
    """
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(
                f"{_BOT_BASE_URL}/admin/test-message",
                json={"message": payload.message, "phone": payload.phone},
                headers=_bot_headers(),
            )
        if r.status_code == 200:
            return r.json()
        raise HTTPException(status_code=502, detail=f"Bot returned {r.status_code}: {r.text[:200]}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Bot test failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Bot unreachable: {exc}")


def _broadcast_templates_for_day(day: int) -> list[dict]:
    """Return the template variants that will be sent on a given broadcast day."""
    if day == 1:
        return [{"key": "live_day1", "label": "Rappel J1 (tous)"}]
    if day == 2:
        return [
            {"key": "live_day2_attended_v2",        "label": "A assisté J1"},
            {"key": "live_day2_registered_absent",   "label": "Inscrit StreamYard mais absent J1"},
            {"key": "live_day2_not_registered",      "label": "Non inscrit StreamYard J1"},
        ]
    if day == 3:
        return [
            {"key": "live_day3_attended_v2",        "label": "A assisté J2"},
            {"key": "live_day3_registered_absent",   "label": "Inscrit StreamYard mais absent J2"},
            {"key": "live_day3_not_registered",      "label": "Non inscrit StreamYard J2"},
        ]
    return []


app = FastAPI()
app.include_router(router)
app.include_router(ops_router)


