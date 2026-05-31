"""AI engine — KB routing + OpenAI fallback avec historique de conversation.

Routing order (from bot-guardrails-system.md):
  1. knowledge_base.kb_lookup()  — deterministic static rules, zero latency
  2. learned_kb_lookup()         — admin-activated rules from Wati training
  3. OpenAI gpt-4o-mini          — generic fallback for unmatched inputs

Returns: {"reply": str, "intent": str, "needs_human": bool}
"""
import logging
import time
import unicodedata

from sqlalchemy.orm import Session

from bot.app.config import get_settings
from bot.app.knowledge_base import kb_lookup
from bot.app.models import (
    CampaignEnrollment,
    ChallengeEdition,
    Contact,
    InboundMessage,
    LearnedKBRule,
)

logger = logging.getLogger(__name__)

# ── Learned KB cache (reloaded from DB every 60 s) ────────────────────────────

_learned_rules_cache: list[dict] = []
_learned_rules_loaded_at: float = 0.0
_LEARNED_RULES_TTL = 60.0


def _norm_learned(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_text.split())


def _reload_learned_rules(db: Session) -> None:
    global _learned_rules_cache, _learned_rules_loaded_at
    rows = db.query(LearnedKBRule).filter(LearnedKBRule.active.is_(True)).all()
    _learned_rules_cache = [
        {
            "intent": r.intent,
            "keywords": [kw.lower() for kw in (r.keywords or [])],
            "reply": r.suggested_reply,
            "needs_human": r.needs_human,
        }
        for r in rows
    ]
    _learned_rules_loaded_at = time.monotonic()
    logger.info("Learned KB cache refreshed — %d active rules", len(_learned_rules_cache))


def learned_kb_lookup(message: str, db: Session) -> dict | None:
    """Check admin-activated learned rules extracted from Wati conversations.

    Refreshes from DB at most once every 60 s to avoid per-message queries.
    Returns same shape as kb_lookup(): {intent, reply, needs_human} or None.
    """
    if time.monotonic() - _learned_rules_loaded_at > _LEARNED_RULES_TTL:
        _reload_learned_rules(db)

    if not _learned_rules_cache:
        return None

    normalised = _norm_learned(message)
    for rule in _learned_rules_cache:
        for kw in rule["keywords"]:
            if kw and kw in normalised:
                return {"intent": rule["intent"], "reply": rule["reply"], "needs_human": rule["needs_human"]}
    return None


_SYSTEM_PROMPT = """\
Tu es l'assistant WhatsApp du Challenge Amazon FBA. Tu réponds au nom de l'équipe organisatrice.

RÈGLES ABSOLUES :
1. Jamais plus de 3 phrases courtes par réponse.
2. Ne promets rien sur les revenus ou les résultats.
3. Ne donne pas de prix exacts — dis "réponds-moi ici et je te transmets les infos".
4. Si quelqu'un évoque un paiement raté, une plainte ou un problème juridique → réponds UNIQUEMENT : "Je transmets ton message à l'équipe qui te recontacte rapidement."
5. Tutoie toujours le contact.
6. Réponds en français, même si le message est en anglais.
7. Sois chaleureux, direct, sans fioriture.

CONTEXTE DU CONTACT :
{contact_context}

LIENS ACTIFS :
{live_links}

Si tu ne sais pas répondre, dis : "Je transmets ta question à l'équipe !"
"""

_FALLBACK_REPLY = "Je transmets ta question à l'équipe qui te répond très vite !"


def _build_contact_context(
    contact: Contact | None,
    enrollment: CampaignEnrollment | None,
    edition: ChallengeEdition | None,
) -> str:
    parts = []
    if contact:
        parts.append(f"Prénom : {contact.first_name or 'inconnu'}")
    if enrollment:
        parts.append(f"Étape actuelle : {enrollment.current_step}")
        parts.append(f"Cohorte : {enrollment.cohort}")
    if edition:
        parts.append(f"Édition : {edition.edition_key} ({edition.edition_date})")
    return "\n".join(parts) if parts else "Contact inconnu (nouveau prospect)"


def _build_live_links(edition: ChallengeEdition | None) -> str:
    if not edition:
        return "Aucun lien actif configuré."
    links = []
    if edition.day1_url:
        links.append(f"Jour 1 : {edition.day1_url}")
    if edition.day2_url:
        links.append(f"Jour 2 : {edition.day2_url}")
    if edition.day3_url:
        links.append(f"Jour 3 : {edition.day3_url}")
    return "\n".join(links) if links else "Aucun lien live actif."


def _load_history(db: Session, phone: str, limit: int) -> list[dict]:
    """Charge les `limit` derniers messages comme turns user/assistant."""
    rows = (
        db.query(InboundMessage)
        .filter(InboundMessage.phone == phone)
        .order_by(InboundMessage.received_at.desc())
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    turns = []
    for row in rows:
        turns.append({"role": "user", "content": row.text})
        if row.ai_reply:
            turns.append({"role": "assistant", "content": row.ai_reply})
    return turns


def generate_reply(
    message: str,
    phone: str,
    db: Session,
    contact: Contact | None,
    enrollment: CampaignEnrollment | None,
    edition: ChallengeEdition | None,
) -> dict:
    """Génère une réponse avec KB-first routing + OpenAI fallback.

    Routing order:
      1. KB lookup  — deterministic rules for common production inputs
      2. OpenAI     — generic fallback for unmatched messages

    Returns: {"reply": str, "intent": str, "needs_human": bool}
    """
    settings = get_settings()

    # ── 1. Static knowledge base (deterministic, zero latency) ───────────────
    kb_result = kb_lookup(message)
    if kb_result is not None:
        logger.info("KB match for %s: intent=%s", phone, kb_result["intent"])
        return kb_result

    # ── 2. Learned rules from Wati training (DB-backed, 60 s cache) ──────────
    learned_result = learned_kb_lookup(message, db)
    if learned_result is not None:
        logger.info("Learned KB match for %s: intent=%s", phone, learned_result["intent"])
        return learned_result

    # ── 3. LLM fallback (OpenAI gpt-4o-mini) ─────────────────────────────────
    if not settings.openai_api_key:
        logger.warning("No OpenAI key — returning fallback reply for %s", phone)
        return {"reply": _FALLBACK_REPLY, "intent": "fallback_no_key", "needs_human": False}

    history = _load_history(db, phone=phone, limit=settings.max_history_messages)

    system = _SYSTEM_PROMPT.format(
        contact_context=_build_contact_context(contact, enrollment, edition),
        live_links=_build_live_links(edition),
    )

    messages = history + [{"role": "user", "content": message}]

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=256,
            temperature=0.35,
        )
        reply_text = response.choices[0].message.content.strip()
        logger.info("OpenAI reply for %s (len=%d)", phone, len(reply_text))
        return {"reply": reply_text, "intent": "ai_generated", "needs_human": False}

    except Exception as exc:
        logger.error("OpenAI error for %s: %s", phone, exc)
        return {"reply": _FALLBACK_REPLY, "intent": "fallback_error", "needs_human": False}
