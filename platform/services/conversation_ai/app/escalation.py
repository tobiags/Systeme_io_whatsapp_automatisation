import unicodedata

from services.conversation_ai.app.prompts import ESCALATION_KEYWORDS


_COMPLEX_PERSONAL_CASE_PHRASES = {
    "cas personnel complexe",
    "situation personnelle complexe",
    "cas complexe",
    "situation complexe",
    "cas particulier",
    "situation particuliere",
    "un peu particulier",
    "un peu complique",
}


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    return (
        unicodedata.normalize("NFKD", lowered)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def needs_human_escalation(text: str) -> bool:
    """Return True if the message requires immediate human handoff."""
    normalized = _normalize_text(text)
    return any(_normalize_text(kw) in normalized for kw in ESCALATION_KEYWORDS) or any(
        phrase in normalized for phrase in _COMPLEX_PERSONAL_CASE_PHRASES
    )
