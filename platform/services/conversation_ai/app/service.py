from services.conversation_ai.app.escalation import needs_human_escalation
from services.conversation_ai.app.prompts import FAQ, FINANCIAL_KEYWORDS


def _keyword_reply(text: str) -> dict | None:
    """Fast local reply using FAQ and keyword rules. Returns None if no match."""
    for faq_key, faq_answer in FAQ.items():
        if faq_key in text:
            return {"reply": faq_answer, "needs_human": False, "intent": "faq"}

    if needs_human_escalation(text):
        return {
            "reply": "Je transmets votre demande à un conseiller qui vous contactera rapidement.",
            "needs_human": True,
            "intent": "human_escalation",
        }

    if any(kw in text for kw in FINANCIAL_KEYWORDS):
        return {
            "reply": "Je comprends votre question sur le budget. Le challenge est gratuit et les détails de la formation sont présentés pendant le parcours.",
            "needs_human": False,
            "intent": "financial_objection",
        }

    return None


def _openai_reply(message: str, api_key: str) -> dict:
    """Call OpenAI GPT to generate a contextual reply about Challenge Amazon FBA."""
    try:
        import httpx

        system_prompt = (
            "Tu es l'assistant IA du Challenge Amazon FBA. "
            "Tu réponds en français, de façon concise et bienveillante. "
            "Le challenge se déroule du jeudi au samedi, 2 fois par mois, en direct WhatsApp. "
            "Si la question dépasse ton cadre (remboursement, juridique, contrat), "
            "dis que tu transmets à un conseiller humain et renvoie needs_human=true."
        )
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            reply_text = resp.json()["choices"][0]["message"]["content"].strip()
            needs_human = any(w in reply_text.lower() for w in ["conseiller", "transmets", "humain"])
            return {
                "reply": reply_text,
                "needs_human": needs_human,
                "intent": "ai_generated",
            }
    except Exception:
        return None  # fall through to default


def build_reply(message: str) -> dict:
    text = message.lower()

    # 1. Fast local rules first (no API cost)
    local = _keyword_reply(text)
    if local:
        return local

    # 2. OpenAI if key is configured
    from shared.config.settings import settings
    if settings.openai_api_key:
        ai = _openai_reply(message, settings.openai_api_key)
        if ai:
            return ai

    # 3. Default fallback
    return {
        "reply": "Merci pour votre message. Un conseiller ou la prochaine étape du challenge vous apportera plus d'informations.",
        "needs_human": False,
        "intent": "default",
    }
