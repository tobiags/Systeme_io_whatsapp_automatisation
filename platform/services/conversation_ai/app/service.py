from services.conversation_ai.app.escalation import needs_human_escalation
from services.conversation_ai.app.prompts import (
    FAQ,
    FINANCIAL_KEYWORDS,
    FINANCIAL_SOFT_KEYWORDS,
    FINANCIAL_STRONG_KEYWORDS,
    INSTALLMENT_KEYWORDS,
    PAYMENT_FAILURE_KEYWORDS,
    SCEPTIC_KEYWORDS,
)


def _keyword_reply(text: str) -> dict | None:
    """
    Fast local reply using FAQ and keyword rules.
    Returns a dict with reply / needs_human / intent, or None if no match.
    """
    # 1. Explicit human escalation (highest priority)
    if needs_human_escalation(text):
        return {
            "reply": "Je transmets votre demande à un conseiller qui vous contactera rapidement.",
            "needs_human": True,
            "intent": "human_escalation",
        }

    # 2. FAQ match (exact keyword substring)
    for faq_key, (faq_answer, faq_intent) in FAQ.items():
        if faq_key in text:
            return {"reply": faq_answer, "needs_human": False, "intent": faq_intent}

    # 3. Payment failure — high priority (needs operator follow-up)
    if any(kw in text for kw in PAYMENT_FAILURE_KEYWORDS):
        return {
            "reply": (
                "Je suis désolé pour ce problème de paiement. "
                "Un conseiller va examiner votre situation et vous recontactera très prochainement."
            ),
            "needs_human": True,
            "intent": "payment_failure_followup_needed",
        }

    # 4. Installment / payment plan request
    if any(kw in text for kw in INSTALLMENT_KEYWORDS):
        return {
            "reply": (
                "Je comprends votre souhait de payer en plusieurs fois. "
                "Je transmets votre demande à notre équipe qui vous présentera les options disponibles."
            ),
            "needs_human": True,
            "intent": "installment_plan_request",
        }

    # 5. Sceptic / trust objection
    if any(kw in text for kw in SCEPTIC_KEYWORDS):
        return {
            "reply": (
                "Je comprends votre hésitation — c'est tout à fait normal. "
                "Le challenge est gratuit et sans engagement. "
                "Vous pouvez voir par vous-même la valeur avant toute décision."
            ),
            "needs_human": False,
            "intent": "skeptic_trust_objection",
        }

    # 6. Strong financial objection
    if any(kw in text for kw in FINANCIAL_STRONG_KEYWORDS):
        return {
            "reply": (
                "Je comprends. Le challenge lui-même est entièrement gratuit — "
                "vous n'avez rien à débourser pour y participer. "
                "La formation complète est une option présentée à la fin pour ceux qui le souhaitent."
            ),
            "needs_human": False,
            "intent": "objection_financial_strong",
        }

    # 7. Soft financial objection
    if any(kw in text for kw in FINANCIAL_SOFT_KEYWORDS):
        return {
            "reply": (
                "Je comprends votre question sur le budget. "
                "Le challenge est gratuit et les détails de la formation sont présentés pendant le parcours."
            ),
            "needs_human": False,
            "intent": "objection_financial_soft",
        }

    # 8. Generic financial keyword (catch-all)
    if any(kw in text for kw in FINANCIAL_KEYWORDS):
        return {
            "reply": (
                "Le challenge est 100% gratuit. "
                "Les informations sur la formation complète sont communiquées pendant et après le challenge."
            ),
            "needs_human": False,
            "intent": "financial_objection",
        }

    return None


def _openai_reply(message: str, api_key: str) -> dict | None:
    """Call OpenAI GPT to generate a contextual reply about Challenge Amazon FBA."""
    try:
        import httpx

        system_prompt = (
            "Tu es l'assistant IA du Challenge Amazon FBA. "
            "Tu réponds en français, de façon concise et bienveillante, adapté à un public débutant. "
            "Le challenge se déroule du jeudi au samedi, 2 fois par mois, en direct WhatsApp. "
            "Il est entièrement gratuit. Une offre de formation est présentée à la fin. "
            "Si la question dépasse ton cadre (remboursement, juridique, contrat, plan de paiement), "
            "dis que tu transmets à un conseiller humain et renvoie needs_human=true. "
            "Réponds toujours en moins de 3 phrases."
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
            needs_human = any(
                w in reply_text.lower()
                for w in ["conseiller", "transmets", "humain", "rappelé", "contactera"]
            )
            return {
                "reply": reply_text,
                "needs_human": needs_human,
                "intent": "ai_generated",
            }
    except Exception:
        return None


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
        "reply": (
            "Merci pour votre message. "
            "Un conseiller ou la prochaine étape du challenge vous apportera plus d'informations."
        ),
        "needs_human": False,
        "intent": "default",
    }
