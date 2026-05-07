from services.conversation_ai.app.prompts import ESCALATION_KEYWORDS


def needs_human_escalation(text: str) -> bool:
    """Return True if the message requires immediate human handoff."""
    normalized = text.lower()
    return any(kw in normalized for kw in ESCALATION_KEYWORDS)
