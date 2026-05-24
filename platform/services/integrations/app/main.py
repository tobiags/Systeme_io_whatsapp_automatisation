import logging
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.db.models import ChallengeEdition, Consent, Contact, ContactScore, InboundMessage, Message, ScoreEvent, Segment
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


def _find_active_edition(db: Session, cohort: str) -> "ChallengeEdition | None":
    """Return the nearest upcoming ChallengeEdition for the given cohort."""
    from datetime import date
    today = date.today().isoformat()
    return (
        db.query(ChallengeEdition)
        .filter(
            ChallengeEdition.cohort == cohort,
            ChallengeEdition.edition_date >= today,
        )
        .order_by(ChallengeEdition.edition_date.asc())
        .first()
    )


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

    edition_date = "-".join(edition_key.split("-")[:3]) if edition_key else ""
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
    variables = {"1": (contact.first_name or "").strip() or "vous"}
    result = provider.send_template(contact.phone, "welcome", variables)
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


def _script_primary_blocker_question() -> str:
    return (
        "Qu'est-ce qui vous bloque le plus aujourd'hui ?\n"
        "1. Le choix du produit\n"
        "2. Le budget\n"
        "3. Le manque de temps\n"
        "4. Je ne sais pas par ou commencer"
    )


def _script_branch_prompt(branch: str) -> str:
    prompts = {
        "product_choice": (
            "C'est justement un des points cles du challenge. On va vous montrer comment eviter les mauvais choix "
            "et reperer un produit plus viable. Aujourd'hui, vous cherchez surtout a comprendre la methode ou a "
            "trouver une idee concrete ?"
        ),
        "budget": (
            "Je comprends. Le challenge est la pour vous donner une vision claire avant d'investir quoi que ce soit. "
            "Votre inquietude porte surtout sur le lancement ou sur l'accompagnement ensuite ?"
        ),
        "time": (
            "Je comprends. Le challenge est fait pour aller a l'essentiel sans vous noyer. "
            "Vous manquez surtout de temps pour apprendre ou pour passer a l'action ?"
        ),
        "getting_started": (
            "C'est normal. Le challenge est justement concu pour remettre les etapes dans le bon ordre. "
            "Aujourd'hui, vous avez surtout besoin de comprendre le fonctionnement ou de voir quoi faire en premier ?"
        ),
    }
    return prompts[branch]


def _script_final_question() -> str:
    return (
        "Parfait. Le plus important pour vous maintenant, c'est surtout de comprendre si ce modele est fait pour vous, "
        "ou de voir comment demarrer proprement ?"
    )


def _script_final_reply(choice: str) -> str:
    replies = {
        "fit": (
            "Parfait. Les prochaines sessions vont justement vous aider a voir si ce modele correspond vraiment a votre "
            "situation. Gardez bien les messages du challenge, on va avancer la-dessus pas a pas."
        ),
        "start": (
            "Parfait. Les prochaines sessions vont justement vous montrer comment demarrer proprement sans vous disperser. "
            "Gardez bien les messages du challenge, on va avancer etape par etape."
        ),
    }
    return replies[choice]


def _detect_primary_blocker(normalized_text: str) -> str | None:
    if normalized_text in {"1", "1.", "1)", "choix du produit"}:
        return "product_choice"
    if normalized_text in {"2", "2.", "2)", "budget"}:
        return "budget"
    if normalized_text in {"3", "3.", "3)", "temps"}:
        return "time"
    if normalized_text in {"4", "4.", "4)", "je ne sais pas par ou commencer"}:
        return "getting_started"

    if any(token in normalized_text for token in {"produit", "vendre", "idee", "niche"}):
        return "product_choice"
    if any(token in normalized_text for token in {"budget", "argent", "capital", "invest"}):
        return "budget"
    if any(token in normalized_text for token in {"temps", "time", "occupe", "dispo"}):
        return "time"
    if any(
        phrase in normalized_text
        for phrase in {"par ou", "ou commencer", "quoi faire", "comment debuter", "debuter", "commencer"}
    ):
        return "getting_started"
    return None


def _detect_secondary_focus(branch: str, normalized_text: str) -> str | None:
    branch_detectors = {
        "product_choice": {
            "method": {"methode", "method", "comprendre", "strategie"},
            "concrete_idea": {"idee", "concrete", "produit", "trouver"},
        },
        "budget": {
            "launch": {"lancement", "lancer", "demarrer", "debut"},
            "coaching": {"accompagnement", "suivi", "formation", "ensuite"},
        },
        "time": {
            "learn": {"apprendre", "comprendre", "me former", "formation"},
            "action": {"action", "passer a l action", "executer", "mettre en place"},
        },
        "getting_started": {
            "understand": {"fonctionnement", "comment ca marche", "comprendre", "methode"},
            "first_step": {"premier", "premiere etape", "quoi faire", "par quoi commencer"},
        },
    }
    numeric_shortcuts = {
        "product_choice": {"1": "method", "2": "concrete_idea"},
        "budget": {"1": "launch", "2": "coaching"},
        "time": {"1": "learn", "2": "action"},
        "getting_started": {"1": "understand", "2": "first_step"},
    }

    if normalized_text in numeric_shortcuts.get(branch, {}):
        return numeric_shortcuts[branch][normalized_text]

    for choice, phrases in branch_detectors.get(branch, {}).items():
        if any(phrase in normalized_text for phrase in phrases):
            return choice
    return None


def _detect_final_guidance(normalized_text: str) -> str | None:
    if any(phrase in normalized_text for phrase in {"fait pour moi", "si ce modele", "si c est pour moi"}):
        return "fit"
    if any(phrase in normalized_text for phrase in {"demarrer", "commencer", "passer a l action", "me lancer"}):
        return "start"
    if normalized_text == "1":
        return "fit"
    if normalized_text == "2":
        return "start"
    return None


def _scripted_conversation_reply(latest_outbound: Message, incoming_text: str, result: dict) -> dict | None:
    variables = latest_outbound.variables or {}
    script_state = variables.get("script_state")
    if not isinstance(script_state, dict):
        return None

    current_intent = result.get("intent", "default")
    if current_intent.startswith("faq_") or current_intent in {
        "human_escalation",
        "help_request_guided_followup",
        "geo_constraint_question",
        "payment_failure_followup_needed",
        "installment_plan_request",
        "skeptic_trust_objection",
        "next_challenge_request",
    }:
        return None
    if current_intent not in _SCRIPT_PRIORITIZED_INTENTS:
        return None

    normalized = _normalize_script_text(incoming_text)
    stage = script_state.get("next_stage")

    if stage == "ask_primary_blocker":
        blocker = _detect_primary_blocker(normalized)
        if blocker:
            return {
                "reply": _script_branch_prompt(blocker),
                "needs_human": False,
                "intent": f"script_primary_blocker_{blocker}",
                "script_state": {
                    "next_stage": "resolve_secondary_focus",
                    "profile": script_state.get("profile"),
                    "branch": blocker,
                },
            }
        if _is_script_acknowledgement(normalized):
            return {
                "reply": _script_primary_blocker_question(),
                "needs_human": False,
                "intent": "script_primary_blocker_question",
                "script_state": script_state,
            }
        return None

    if stage == "resolve_secondary_focus":
        branch = script_state.get("branch")
        if not branch:
            return None
        focus = _detect_secondary_focus(branch, normalized)
        if focus:
            return {
                "reply": _script_final_question(),
                "needs_human": False,
                "intent": f"script_secondary_focus_{branch}_{focus}",
                "script_state": {
                    "next_stage": "final_guidance",
                    "profile": script_state.get("profile"),
                    "branch": branch,
                    "focus": focus,
                },
            }
        if _is_script_acknowledgement(normalized):
            return {
                "reply": _script_branch_prompt(branch),
                "needs_human": False,
                "intent": f"script_secondary_focus_reprompt_{branch}",
                "script_state": script_state,
            }
        return None

    if stage == "final_guidance":
        choice = _detect_final_guidance(normalized)
        if choice:
            return {
                "reply": _script_final_reply(choice),
                "needs_human": False,
                "intent": f"script_final_guidance_{choice}",
            }
        if _is_script_acknowledgement(normalized):
            return {
                "reply": _script_final_question(),
                "needs_human": False,
                "intent": "script_final_guidance_question",
                "script_state": script_state,
            }
    return None


def _contextual_default_reply(
    db: Session,
    contact_id: str | None,
    incoming_text: str,
    result: dict,
) -> dict:
    """Use the last outbound message as lightweight conversation state.

    When the classifier falls back to `default`, we still want the bot to act
    inside the boundaries of the last campaign question instead of sounding
    absent or generic.
    """
    if not contact_id:
        return result

    latest_outbound = (
        db.query(Message)
        .filter(Message.contact_id == contact_id)
        .order_by(Message.created_at.desc())
        .first()
    )
    if not latest_outbound:
        return result

    if latest_outbound.template_key == "ai_session_reply":
        scripted = _scripted_conversation_reply(latest_outbound, incoming_text, result)
        if scripted:
            return scripted

    if result.get("intent") not in {"default", "clarification_request", "acknowledgement_no_reply"}:
        return result
    if _looks_like_question(incoming_text):
        return result

    normalized = (incoming_text or "").strip().lower()
    generic_ack = normalized in {
        "bonjour",
        "bonsoir",
        "salut",
        "ok",
        "oui",
        "oui ok",
        "merci",
    }

    template_key = latest_outbound.template_key
    if template_key == "welcome" and generic_ack:
        return {
            "reply": (
                "Bonjour et bienvenue. Les informations principales te seront envoyees avant chaque session, "
                "et si tu as une question simple sur l'organisation du challenge, je peux t'aider ici."
            ),
            "needs_human": False,
            "intent": "welcome_followup_reprompt",
        }

    if template_key == "countdown_j6":
        return {
            "reply": (
                "Merci, c'est note. Pendant le challenge, on reviendra justement "
                "sur les freins comme le temps, le budget et le choix du produit."
            ),
            "needs_human": False,
            "intent": "countdown_j6_followup_reprompt",
        }

    if template_key == "countdown_j5":
        return {
            "reply": (
                "Merci pour votre retour. Le challenge va justement clarifier "
                "le choix du produit, la logistique Amazon et le lancement."
            ),
            "needs_human": False,
            "intent": "countdown_j5_followup_reprompt",
        }

    if template_key == "countdown_j3":
        return {
            "reply": (
                "Merci. Sur les prochaines sessions, on va couvrir "
                "le choix du produit, le lancement et la rentabilite."
            ),
            "needs_human": False,
            "intent": "countdown_j3_followup_reprompt",
        }

    if template_key == "countdown_j2" and generic_ack:
        return {
            "reply": (
                "Parfait. Si vous avez une question pratique avant le debut, "
                "ecrivez-moi ici et je vous repondrai."
            ),
            "needs_human": False,
            "intent": "countdown_j2_followup_reprompt",
        }

    if template_key == "ai_session_reply":
        latest_inbound = (
            db.query(InboundMessage)
            .filter(
                InboundMessage.contact_id == contact_id,
                InboundMessage.intent != "default",
            )
            .order_by(InboundMessage.received_at.desc())
            .first()
        )
        prior_intent = latest_inbound.intent if latest_inbound else ""

        if prior_intent == "beginner_profile":
            return {
                "reply": (
                    _script_primary_blocker_question()
                ),
                "needs_human": False,
                "intent": "script_primary_blocker_question",
                "script_state": {
                    "next_stage": "ask_primary_blocker",
                    "profile": "beginner",
                },
            }

        if prior_intent == "started_profile":
            return {
                "reply": (
                    _script_primary_blocker_question()
                ),
                "needs_human": False,
                "intent": "script_primary_blocker_question",
                "script_state": {
                    "next_stage": "ask_primary_blocker",
                    "profile": "started",
                },
            }

    return result


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

    result = build_reply(text)
    result = _contextual_default_reply(db, contact_id, text, result)
    message_is_question = _looks_like_question(text)

    # Unknown contact or broad unknown question -> do not improvise a bot reply.
    if (
        (not contact_id and not str(result.get("intent", "")).startswith("faq_"))
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
        else _no_auto_reply_delivery("awaiting_human")
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

    day_number = payload.get("day_number")  # optional: 1, 2 or 3

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
        edition = _get_or_create_edition(
            db,
            edition_key=edition_key,
            cohort=cohort,
            campaign_key=campaign_key,
        )
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
            )
            scheduled_count = len(scheduled)
        except Exception as exc:
            logger.error("Failed to schedule tasks for edition %s: %s", edition_key, exc)

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
        local_msg_id = payload.get("localMessageId", "")
        msg_row = _find_message_by_provider_id(db, local_msg_id)
        if msg_row:
            msg_row.status = "delivered"
            db.commit()
        return {"status": "acknowledged", "eventType": event_type}

    # ── Read receipt → record opened_message score event ─────────────────────
    if event_type == "sentMessageREAD_v2":
        local_msg_id = payload.get("localMessageId", "")
        if local_msg_id:
            msg_row = _find_message_by_provider_id(db, local_msg_id)
            if msg_row and msg_row.contact_id:
                msg_row.status = "read"
                _record_score_event(db, msg_row.contact_id, "opened_message")
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

    return process_inbound_wati_message(db, phone, text)

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
    if contact_id:
        _record_score_event(db, contact_id, "replied_message")
        if _looks_like_question(text):
            _record_score_event(db, contact_id, "asked_question")
    db.commit()
    db.refresh(inbound)

    delivery = _send_ai_session_reply(db, phone, contact_id, result["reply"])

    # ── Closer notification for high-intent prospects ─────────────────────────
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
        "où ",
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


@ops_router.post("/session", status_code=status.HTTP_202_ACCEPTED)
def ops_streamyard_session(
    payload: StreamYardSessionUpdatePayload,
    _: str = Depends(_require_ops_token),
    db: Session = Depends(get_db),
):
    return streamyard_session(payload.model_dump(), db)


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


app = FastAPI()
app.include_router(router)
app.include_router(ops_router)
