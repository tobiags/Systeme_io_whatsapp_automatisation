"""AI engine — KB routing + OpenAI fallback avec historique de conversation.

Routing order (from bot-guardrails-system.md):
  1. knowledge_base.kb_lookup()  — deterministic, zero latency, zero cost
  2. OpenAI gpt-4o-mini           — generic fallback for unmatched inputs

This order prevents the LLM from drifting on short inputs like "1", "merci",
"de zero" that a KB rule handles better and more consistently.

Returns: {"reply": str, "intent": str, "needs_human": bool}
"""
import logging

from sqlalchemy.orm import Session

from bot.app.config import get_settings
from bot.app.knowledge_base import kb_lookup
from bot.app.models import (
    CampaignEnrollment,
    ChallengeEdition,
    Contact,
    InboundMessage,
)

logger = logging.getLogger(__name__)

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

    # ── 1. Knowledge base lookup (deterministic, zero latency) ────────────────
    kb_result = kb_lookup(message)
    if kb_result is not None:
        logger.info(
            "KB match for %s: intent=%s needs_human=%s",
            phone, kb_result["intent"], kb_result["needs_human"],
        )
        return kb_result

    # ── 2. LLM fallback (OpenAI gpt-4o-mini) ─────────────────────────────────
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
