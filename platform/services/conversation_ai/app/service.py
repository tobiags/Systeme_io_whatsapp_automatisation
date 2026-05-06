from services.conversation_ai.app.escalation import needs_human_escalation
from services.conversation_ai.app.prompts import FAQ, FINANCIAL_KEYWORDS


def build_reply(message: str) -> dict:
    text = message.lower()

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

    return {
        "reply": "Merci pour votre message. Un conseiller ou la prochaine étape du challenge vous apportera plus d'informations.",
        "needs_human": False,
        "intent": "default",
    }
