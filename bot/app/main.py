"""WhatsApp bot — standalone FastAPI service.

Webhook: POST /webhook/wati   (called by Wati on every incoming message)
Health:  GET  /health
Admin:   GET  /admin/stats    (X-Bot-Key required)
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from bot.app.config import get_settings
from bot.app.db import get_session
from bot.app.engine import generate_reply
from bot.app.guardrails import has_offer_interest, has_question, is_critical
from bot.app.models import (
    CampaignEnrollment,
    ChallengeEdition,
    Contact,
    InboundMessage,
    ScoreEvent,
)
from bot.app.wati_client import send_session_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Bot", version="1.0.0")

settings = get_settings()


# ── DB dependency ─────────────────────────────────────────────────────────────

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# ── Admin auth ────────────────────────────────────────────────────────────────

def require_bot_key(x_bot_key: str = Header(default="")):
    if settings.bot_api_key and x_bot_key != settings.bot_api_key:
        raise HTTPException(status_code=401, detail="Invalid X-Bot-Key")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_phone(phone: str) -> str:
    p = phone.strip()
    if p.startswith("+"):
        p = p[1:]
    elif p.startswith("00"):
        p = p[2:]
    return p


def _is_duplicate(db: Session, phone: str, text: str, window_seconds: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    existing = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.phone == phone,
            InboundMessage.text == text,
            InboundMessage.received_at >= cutoff,
        )
        .first()
    )
    return existing is not None


def _record_score(db: Session, contact_id: str, event_type: str, points: int):
    db.add(ScoreEvent(contact_id=contact_id, event_type=event_type, points=points))


def _get_active_enrollment(db: Session, contact_id: str) -> CampaignEnrollment | None:
    return (
        db.query(CampaignEnrollment)
        .filter(CampaignEnrollment.contact_id == contact_id)
        .order_by(CampaignEnrollment.created_at.desc())
        .first()
    )


def _get_edition(db: Session, edition_key: str | None) -> ChallengeEdition | None:
    if not edition_key:
        return None
    return (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )


# ── Webhook ───────────────────────────────────────────────────────────────────

@app.post("/webhook/wati")
async def wati_webhook(request: Request, db: Session = Depends(get_db)):
    """Process all incoming Wati events.

    Only `messageReceived` events trigger a bot reply.
    Other events (delivery receipts, etc.) are acknowledged silently.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid_json"})

    event_type = payload.get("eventType", "")

    # Only process inbound messages
    if event_type != "messageReceived":
        return {"ok": True, "event": event_type, "action": "ignored"}

    phone_raw = payload.get("waId") or payload.get("id", "")
    text = (payload.get("text") or "").strip()
    sender_name = payload.get("senderName", "")

    if not phone_raw or not text:
        return {"ok": True, "action": "skipped_empty"}

    phone = _normalise_phone(phone_raw)

    logger.info("Inbound from %s: %r", phone, text[:80])

    # Duplicate guard
    if _is_duplicate(db, phone, text, settings.dedup_window_seconds):
        logger.info("Duplicate message from %s — skipping", phone)
        return {"ok": True, "action": "dedup_skip"}

    # Auto-reply disabled globally
    if not settings.auto_reply_enabled:
        db.add(InboundMessage(
            phone=phone,
            text=text,
            ai_reply=None,
            needs_human=True,
            intent="auto_reply_disabled",
        ))
        db.commit()
        return {"ok": True, "action": "auto_reply_disabled"}

    # Load contact
    contact = db.query(Contact).filter(Contact.phone == phone).first()
    enrollment = _get_active_enrollment(db, contact.id) if contact else None
    edition = _get_edition(db, enrollment.edition_key if enrollment else None)

    # ── Guardrails ────────────────────────────────────────────────────────────
    if is_critical(text):
        logger.info("Critical message from %s — escalating to human", phone)
        reply = "Je transmets ton message à l'équipe qui te recontacte rapidement."
        db.add(InboundMessage(
            phone=phone,
            contact_id=contact.id if contact else None,
            text=text,
            ai_reply=reply,
            needs_human=True,
            intent="human_escalation",
        ))
        db.commit()
        send_session_message(phone, reply)
        _notify_closer(phone, sender_name, text, "human_escalation")
        return {"ok": True, "intent": "human_escalation", "reply_sent": True}

    # ── Generate AI reply ─────────────────────────────────────────────────────
    result = generate_reply(
        message=text,
        phone=phone,
        db=db,
        contact=contact,
        enrollment=enrollment,
        edition=edition,
    )

    reply = result["reply"]
    intent = result["intent"]
    needs_human = result["needs_human"]

    # ── Score events ──────────────────────────────────────────────────────────
    if contact:
        _record_score(db, contact.id, "replied_message", 10)
        if has_question(text):
            _record_score(db, contact.id, "asked_question", 20)
        if has_offer_interest(text):
            _record_score(db, contact.id, "offer_interest_detected", 20)
            needs_human = True
            _notify_closer(phone, sender_name, text, "offer_interest")

    # ── Persist audit ─────────────────────────────────────────────────────────
    db.add(InboundMessage(
        phone=phone,
        contact_id=contact.id if contact else None,
        text=text,
        ai_reply=reply,
        needs_human=needs_human,
        intent=intent,
    ))
    db.commit()

    # ── Send reply ────────────────────────────────────────────────────────────
    delivery = send_session_message(phone, reply)
    logger.info("Reply sent to %s (intent=%s, delivery=%s)", phone, intent, delivery.get("status"))

    return {
        "ok": True,
        "phone": phone,
        "intent": intent,
        "needs_human": needs_human,
        "reply": reply,
        "delivery": delivery,
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "auto_reply": settings.auto_reply_enabled,
        "claude_model": settings.claude_model,
    }


# ── Admin stats ───────────────────────────────────────────────────────────────

@app.get("/admin/stats", dependencies=[Depends(require_bot_key)])
def stats(db: Session = Depends(get_db)):
    from sqlalchemy import func, text

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    total = db.query(func.count(InboundMessage.id)).scalar()
    last_24h = (
        db.query(func.count(InboundMessage.id))
        .filter(InboundMessage.received_at >= cutoff_24h)
        .scalar()
    )
    needs_human = (
        db.query(func.count(InboundMessage.id))
        .filter(InboundMessage.needs_human.is_(True))
        .filter(InboundMessage.received_at >= cutoff_24h)
        .scalar()
    )
    by_intent = (
        db.query(InboundMessage.intent, func.count(InboundMessage.id))
        .filter(InboundMessage.received_at >= cutoff_24h)
        .group_by(InboundMessage.intent)
        .all()
    )
    return {
        "total_inbound_all_time": total,
        "last_24h": last_24h,
        "needs_human_last_24h": needs_human,
        "by_intent_last_24h": {intent: count for intent, count in by_intent},
    }


@app.post("/admin/auto-reply/toggle", dependencies=[Depends(require_bot_key)])
def toggle_auto_reply(enabled: bool):
    """Enable or disable the bot auto-reply at runtime (no restart needed)."""
    settings.auto_reply_enabled = enabled
    return {"auto_reply_enabled": settings.auto_reply_enabled}


# ── Closer notification ───────────────────────────────────────────────────────

def _notify_closer(phone: str, name: str, text: str, reason: str):
    if not settings.closer_email or not settings.smtp_host:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText

        body = (
            f"Escalade WhatsApp — {reason}\n\n"
            f"Téléphone : +{phone}\n"
            f"Nom Wati : {name}\n"
            f"Message : {text}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"[Bot FBA] Escalade {reason} — +{phone}"
        msg["From"] = settings.smtp_from
        msg["To"] = settings.closer_email

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            for addr in settings.closer_email.split(","):
                server.sendmail(settings.smtp_from, addr.strip(), msg.as_string())
    except Exception as exc:
        logger.error("Closer notification failed: %s", exc)
