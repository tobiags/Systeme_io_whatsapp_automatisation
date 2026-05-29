"""AI engine — Claude with full conversation history.

Improvements over the legacy bot:
- Loads last N inbound+outbound messages as conversation turns (real memory)
- System prompt knows the contact's journey step, cohort, live links
- Returns structured dict: {reply, intent, needs_human}
- Falls back gracefully if Anthropic key is not set
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from bot.app.config import get_settings
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


def _load_history(db: Session, phone: str, contact_id: str | None, limit: int) -> list[dict]:
    """Load last `limit` inbound messages as alternating user/assistant turns."""
    rows = (
        db.query(InboundMessage)
        .filter(InboundMessage.phone == phone)
        .order_by(InboundMessage.received_at.desc())
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))  # oldest first
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
    """Generate an AI reply using Claude with conversation history.

    Returns:
        {"reply": str, "intent": str, "needs_human": bool}
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        return {"reply": _FALLBACK_REPLY, "intent": "fallback_no_key", "needs_human": False}

    history = _load_history(
        db,
        phone=phone,
        contact_id=contact.id if contact else None,
        limit=settings.max_history_messages,
    )

    system = _SYSTEM_PROMPT.format(
        contact_context=_build_contact_context(contact, enrollment, edition),
        live_links=_build_live_links(edition),
    )

    messages = history + [{"role": "user", "content": message}]

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=256,
            system=system,
            messages=messages,
        )
        reply_text = response.content[0].text.strip()
        return {"reply": reply_text, "intent": "ai_generated", "needs_human": False}

    except Exception as exc:
        logger.error("Claude API error: %s", exc)
        return {"reply": _FALLBACK_REPLY, "intent": "fallback_error", "needs_human": False}
