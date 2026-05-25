import re
import unicodedata
from difflib import SequenceMatcher

from services.conversation_ai.app.escalation import needs_human_escalation
from services.conversation_ai.app.knowledge_base import KB_GUARDRAIL_RULES
from services.conversation_ai.app.prompts import (
    BEGINNER_PROFILE_KEYWORDS,
    FAQ,
    FINANCIAL_KEYWORDS,
    FINANCIAL_SOFT_KEYWORDS,
    FINANCIAL_STRONG_KEYWORDS,
    INSTALLMENT_KEYWORDS,
    NEXT_CHALLENGE_REQUEST_KEYWORDS,
    PAYMENT_FAILURE_KEYWORDS,
    PRODUCT_CHOICE_KEYWORDS,
    SCEPTIC_KEYWORDS,
    STARTED_PROFILE_KEYWORDS,
    TIME_OBJECTION_KEYWORDS,
)


_ACKNOWLEDGEMENT_PHRASES = {
    "ok",
    "okay",
    "ok merci",
    "merci",
    "bonjour",
    "bien recu",
    "recu",
    "vu",
    "compris",
    "d accord",
    "daccord",
    "cool",
    "super",
    "parfait",
    "tres bien",
}

_EXPLICIT_INTEREST_PHRASES = [
    "ca m interesse",
    "je veux en savoir plus",
    "je suis interesse",
    "je suis interessee",
    "dis m en plus",
    "c est pour moi",
    "j aimerais",
    "je veux participer",
    "comment s inscrire",
]

_ESCALATE_NOW_PHRASES = [
    "je veux acheter",
    "quel est le prix",
    "combien ca coute",
    "combien coute",
    "je veux rejoindre",
    "je veux rejoindre le programme",
    "rappelle moi",
    "appelle moi",
    "probleme de paiement",
    "paiement refuse",
    "plainte",
    "remboursement",
]

_SELF_SERVICE_FAQ_INTENTS = {
    "faq_start_time",
    "faq_challenge_overview",
    "faq_whatsapp_group_join",
}


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    ascii_text = (
        unicodedata.normalize("NFKD", lowered)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    ascii_text = re.sub(r"[^\w\s]", " ", ascii_text)
    # Normalize common lead typos like "zer0" -> "zero" without changing
    # standalone digits such as "0", which we route separately.
    ascii_text = re.sub(r"(?<=[a-z])0(?=[a-z]|\b)", "o", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _contains_approx_phrase(normalized_text: str, phrase: str, *, threshold: float = 0.9) -> bool:
    normalized_phrase = _normalize_text(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    if normalized_phrase in normalized_text:
        return True

    text_tokens = normalized_text.split()
    phrase_tokens = normalized_phrase.split()
    phrase_len = len(phrase_tokens)
    if not text_tokens or phrase_len == 0 or len(text_tokens) < phrase_len:
        return SequenceMatcher(None, normalized_text, normalized_phrase).ratio() >= threshold

    for start in range(len(text_tokens) - phrase_len + 1):
        window = " ".join(text_tokens[start : start + phrase_len])
        if SequenceMatcher(None, window, normalized_phrase).ratio() >= threshold:
            return True

    return SequenceMatcher(None, normalized_text, normalized_phrase).ratio() >= threshold


def _matches_any_phrase(normalized_text: str, phrases: list[str], *, threshold: float = 0.9) -> bool:
    return any(_contains_approx_phrase(normalized_text, phrase, threshold=threshold) for phrase in phrases)


def _detect_signal_level(normalized_text: str) -> str:
    if _matches_any_phrase(normalized_text, _ESCALATE_NOW_PHRASES, threshold=0.88):
        return "escalate"
    if _matches_any_phrase(normalized_text, _EXPLICIT_INTEREST_PHRASES, threshold=0.88):
        return "interest"
    if normalized_text in _ACKNOWLEDGEMENT_PHRASES or len(normalized_text) <= 4:
        return "acquittal"
    return "unknown"


def _knowledge_base_reply(normalized_text: str) -> dict | None:
    for rule in KB_GUARDRAIL_RULES:
        if normalized_text in rule.get("exact_messages", set()):
            payload = {
                "reply": rule["reply"],
                "needs_human": rule["needs_human"],
                "intent": rule["intent"],
            }
            if "script_state" in rule:
                payload["script_state"] = rule["script_state"]
            return payload

        if _matches_any_phrase(
            normalized_text,
            rule.get("keywords", []),
            threshold=rule.get("threshold", 0.9),
        ):
            payload = {
                "reply": rule["reply"],
                "needs_human": rule["needs_human"],
                "intent": rule["intent"],
            }
            if "script_state" in rule:
                payload["script_state"] = rule["script_state"]
            return payload
    return None


def _interest_followup_payload(normalized_text: str) -> dict:
    if any(token in normalized_text for token in {"dispo", "disponible", "horaire", "libre"}):
        return {
            "reply": "Top. C'est surtout votre disponibilite pour suivre les lives qui vous preoccupe aujourd'hui ?",
            "intent": "interest_followup_availability",
            "script_state": {"next_stage": "awaiting_interest_followup", "topic": "availability"},
        }
    if any(token in normalized_text for token in {"bloque", "frein", "difficulte", "probleme"}):
        return {
            "reply": "D'accord. Quel est votre frein principal aujourd'hui pour avancer sur ce projet ?",
            "intent": "interest_followup_obstacle",
            "script_state": {"next_stage": "awaiting_interest_followup", "topic": "obstacle"},
        }
    return {
        "reply": "Qu'est-ce que vous cherchez surtout a obtenir avec ce challenge aujourd'hui ?",
        "intent": "interest_followup_objective",
        "script_state": {"next_stage": "awaiting_interest_followup", "topic": "objective"},
    }


def _keyword_reply(text: str) -> dict | None:
    """
    Fast local reply using FAQ, signal-level routing and a few guarded topic handlers.
    """
    normalized_text = _normalize_text(text)

    if needs_human_escalation(normalized_text):
        return {
            "reply": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
            "needs_human": True,
            "intent": "human_escalation",
        }

    knowledge = _knowledge_base_reply(normalized_text)
    if knowledge:
        return knowledge

    signal_level = _detect_signal_level(normalized_text)

    if signal_level == "escalate":
        return {
            "reply": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
            "needs_human": True,
            "intent": "human_escalation",
        }

    if signal_level == "acquittal":
        return {
            "reply": "N'hesite pas si t'as une question sur le challenge.",
            "needs_human": False,
            "intent": "soft_open_invitation",
        }

    for faq_key, (faq_answer, faq_intent) in FAQ.items():
        if _contains_approx_phrase(normalized_text, faq_key, threshold=0.88):
            if faq_intent in _SELF_SERVICE_FAQ_INTENTS:
                return {"reply": faq_answer, "needs_human": False, "intent": faq_intent}
            break

    if signal_level == "interest":
        followup = _interest_followup_payload(normalized_text)
        return {
            "reply": followup["reply"],
            "needs_human": False,
            "intent": followup["intent"],
            "script_state": followup["script_state"],
        }

    if _matches_any_phrase(normalized_text, BEGINNER_PROFILE_KEYWORDS, threshold=0.88):
        return {
            "reply": (
                "Merci pour ton retour. Ce point sera justement aborde pendant le challenge, "
                "de facon claire et concrete."
            ),
            "needs_human": False,
            "intent": "restricted_beginner_profile",
        }

    if _matches_any_phrase(normalized_text, STARTED_PROFILE_KEYWORDS, threshold=0.88):
        return {
            "reply": (
                "Merci pour ton retour. Le challenge va justement remettre les points importants "
                "dans le bon ordre pour avancer proprement."
            ),
            "needs_human": False,
            "intent": "restricted_started_profile",
        }

    if _matches_any_phrase(normalized_text, TIME_OBJECTION_KEYWORDS, threshold=0.9):
        return {
            "reply": (
                "Merci pour ton retour. Ce point sera aborde pendant le challenge pour vous aider "
                "a y voir plus clair."
            ),
            "needs_human": False,
            "intent": "restricted_main_obstacle",
        }

    if _matches_any_phrase(normalized_text, PRODUCT_CHOICE_KEYWORDS, threshold=0.9):
        return {
            "reply": (
                "Merci pour ton retour. Le choix du produit sera justement traite pendant le challenge, "
                "de maniere simple et concrete."
            ),
            "needs_human": False,
            "intent": "restricted_product_choice",
        }

    if (("peux tu m aider" in normalized_text or "aide moi" in normalized_text) and ("entrainer" in normalized_text or "maintenant" in normalized_text)):
        followup = _interest_followup_payload(normalized_text)
        return {
            "reply": followup["reply"],
            "needs_human": False,
            "intent": followup["intent"],
            "script_state": followup["script_state"],
        }

    if "je vis en" in normalized_text and ("affecter" in normalized_text or "objectif" in normalized_text):
        return {
            "reply": (
                "Le fait de vivre en Haiti n'empeche pas de suivre le challenge. "
                "Si tu veux, precise simplement ce qui te preoccupe le plus et je te repondrai clairement."
            ),
            "needs_human": False,
            "intent": "geo_constraint_question",
        }

    if _matches_any_phrase(normalized_text, PAYMENT_FAILURE_KEYWORDS, threshold=0.9):
        return {
            "reply": "Je transmets ta demande a l'equipe 🙏",
            "needs_human": True,
            "intent": "payment_failure_followup_needed",
        }

    if _matches_any_phrase(normalized_text, INSTALLMENT_KEYWORDS, threshold=0.9):
        return {
            "reply": "Je transmets ta demande a l'equipe 🙏",
            "needs_human": True,
            "intent": "installment_plan_request",
        }

    if _matches_any_phrase(normalized_text, SCEPTIC_KEYWORDS, threshold=0.9):
        return {
            "reply": "Je transmets ta demande a l'equipe 🙏",
            "needs_human": True,
            "intent": "skeptic_trust_objection",
        }

    if _matches_any_phrase(normalized_text, NEXT_CHALLENGE_REQUEST_KEYWORDS, threshold=0.9):
        return {
            "reply": "N'hesite pas si t'as une question sur le challenge 😊",
            "needs_human": False,
            "intent": "soft_open_invitation",
        }

    if _matches_any_phrase(normalized_text, FINANCIAL_STRONG_KEYWORDS, threshold=0.9):
        return {
            "reply": "Je transmets ta demande a l'equipe 🙏",
            "needs_human": True,
            "intent": "objection_financial_strong",
        }

    if _matches_any_phrase(normalized_text, FINANCIAL_SOFT_KEYWORDS, threshold=0.9):
        return {
            "reply": "Je transmets ta demande a l'equipe 🙏",
            "needs_human": True,
            "intent": "objection_financial_soft",
        }

    if _matches_any_phrase(normalized_text, FINANCIAL_KEYWORDS, threshold=0.95):
        return {
            "reply": "Je transmets ta demande a l'equipe 🙏",
            "needs_human": True,
            "intent": "financial_objection",
        }

    return None

_SYSTEM_PROMPT = """Tu es l'assistant IA du Challenge Amazon FBA, un Ã©vÃ©nement gratuit de 3 sessions live diffusÃ© via WhatsApp.

## Ton rÃ´le

Tu rÃ©ponds aux messages WhatsApp des participants du challenge en franÃ§ais, de faÃ§on conversationnelle, bienveillante et concise. Tu es leur guide pendant le challenge â€” pas un vendeur, pas un robot.

## Le Challenge Amazon FBA

**Format :** 3 sessions live consÃ©cutives (jeudiâ€“samedi), 2 fois par mois.
**AccÃ¨s :** 100% gratuit, via lien StreamYard envoyÃ© avant chaque session.
**Programme des sessions :**
- Jour 1 : La mÃ©thode Amazon FBA de A Ã  Z â€” comment Ã§a fonctionne, pourquoi Ã§a marche
- Jour 2 : Trouver et sourcer son produit gagnant â€” critÃ¨res, outils, fournisseurs
- Jour 3 : Lancer et scaler sur Amazon â€” Ã©tapes concrÃ¨tes, stratÃ©gie de rentabilitÃ© + prÃ©sentation d'une offre d'accompagnement

**Ce que les participants veulent vraiment :** Pas "Amazon FBA" â€” ils veulent la libertÃ© financiÃ¨re, un revenu passif, sortir du salariat, construire quelque chose Ã  eux. Parle toujours en termes de rÃ©sultats concrets, pas de fonctionnalitÃ©s.

## Ton style de communication

- Conversationnel, chaleureux, humain â€” comme un mentor qui rÃ©pond Ã  un message WhatsApp
- Phrases courtes. Paragraphes de 1-2 lignes maximum.
- Jamais de discours commercial agressif â€” donne de la valeur avant de demander quoi que ce soit
- Utilise "vous" sauf si le contact utilise "tu" en premier
- Ã‰mojis avec modÃ©ration (1-2 par message max), uniquement si naturels dans le contexte
- Maximum 3 phrases par rÃ©ponse â€” si le sujet est complexe, propose d'en parler avec un conseiller

## Comment gÃ©rer les situations courantes

### Le contact pose une question sur le challenge
â†’ RÃ©ponds prÃ©cisÃ©ment et aide-le Ã  continuer. Mentionne ce qu'il va apprendre s'il reste engagÃ©.

### Le contact rÃ©pond Ã  une question posÃ©e dans un message du challenge
â†’ Ne rÃ©ponds jamais comme si son message tombait de nulle part.
â†’ Reprends explicitement le fil de la conversation et valide sa rÃ©ponse.
â†’ Ne pose une nouvelle question que si elle est strictement nÃ©cessaire pour faire avancer la personne.
â†’ Si une rÃ©ponse simple suffit, arrÃªte-toi aprÃ¨s l'explication.
â†’ Exemples :
- "Je pars de zÃ©ro" â†’ rassure, explique que le challenge est pensÃ© pour Ã§a, sans relance commerciale.
- "Je veux commencer" â†’ encourage et oriente vers la suite du challenge.
- "Mon frein c'est le temps" â†’ valide et simplifie, sans forcer une nouvelle question.
- "Je ne sais pas quoi vendre" â†’ rassure et rappelle que Jour 2 traite prÃ©cisÃ©ment ce sujet.

### Le contact dit qu'il a manquÃ© une session
â†’ Rappelle-lui qu'il peut rejoindre la prochaine session mÃªme en ayant ratÃ© la prÃ©cÃ©dente. Chaque session apporte de la valeur indÃ©pendamment. Ne juge pas l'absence.

### Le contact exprime des doutes ou de la fatigue
â†’ Valide son ressenti. Rappelle-lui pourquoi il s'est inscrit (il cherchait un changement). Propose une action simple et immÃ©diate.
â†’ Exemple : "Je comprends, c'est normal d'avoir des doutes. La bonne nouvelle, c'est que vous avez dÃ©jÃ  fait le plus dur en vous inscrivant. Ce soir Ã  [heure], il suffit de cliquer sur le lien."

### Le contact montre de l'intÃ©rÃªt pour l'offre de formation
â†’ Sois enthousiaste mais sans pression. Explique que l'offre est rÃ©servÃ©e aux participants de cette Ã©dition et que les dÃ©tails sont prÃ©sentÃ©s en Jour 3. Si le Jour 3 est terminÃ©, transmets Ã  un conseiller.
â†’ Mots-clÃ©s qui signalent l'intÃ©rÃªt : "intÃ©ressÃ©", "combien Ã§a coÃ»te", "comment Ã§a marche", "je veux aller plus loin", "OUI", "oui"

### Le contact hÃ©site sur le prix de la formation
â†’ Ne donne jamais de prix par message â€” renvoie vers un conseiller.
â†’ Rappelle d'abord la valeur reÃ§ue gratuitement (3 sessions, mÃ©thode complÃ¨te).
â†’ Exemple : "Vous avez dÃ©jÃ  reÃ§u la mÃ©thode complÃ¨te gratuitement. La formation, c'est l'accompagnement pour la mettre en Å“uvre avec un filet de sÃ©curitÃ©. Je transmets votre question Ã  notre Ã©quipe qui vous donnera tous les dÃ©tails."

### Le contact est sceptique (arnaque, trop beau pour Ãªtre vrai)
â†’ Valide sa mÃ©fiance â€” c'est sain. Rappelle que le challenge est gratuit et sans engagement.
â†’ Exemple : "C'est une excellente rÃ©flexe d'Ãªtre prudent. Le challenge est 100% gratuit â€” vous n'avez rien Ã  perdre Ã  suivre les 3 sessions et Ã  juger par vous-mÃªme."

### Le contact veut Ãªtre rappelÃ© ou parler Ã  quelqu'un
â†’ Transmets immÃ©diatement Ã  un conseiller (needs_human: true).

## RÃ¨gles absolues

1. **Ne donne jamais de prix** â€” renvoie vers un conseiller humain
2. **Ne promets jamais de rÃ©sultats garantis** â€” Amazon FBA est un vrai business qui demande du travail
3. **Ne mens jamais** sur le contenu ou le format du challenge
4. **Si tu ne sais pas** â†’ dis-le honnÃªtement et propose de transmettre Ã  un conseiller
5. **3 phrases maximum** par rÃ©ponse
6. **needs_human: true** si : demande de remboursement, problÃ¨me de paiement, demande d'appel, contenu juridique, plainte, situation personnelle complexe
7. **N'envoie jamais une relance commerciale gÃ©nÃ©rique** juste pour remplir le silence
8. **N'envoie pas deux fois la mÃªme idÃ©e** si la rÃ©ponse risque de paraÃ®tre rÃ©pÃ©titive ou robotisÃ©e
9. **PrÃ©fÃ¨re une rÃ©ponse courte sans question** Ã  une question artificielle ou trop vendeuse

## Signaux d'intÃ©rÃªt commercial Ã  dÃ©tecter

Si le contact dit "OUI", "oui", "je suis intÃ©ressÃ©", "comment aller plus loin", "je veux rejoindre" â†’ renvoie-le vers le conseiller (needs_human: true) avec la rÃ©ponse :
"Super nouvelle ! ðŸŽ‰ Je transmets votre intÃ©rÃªt Ã  notre Ã©quipe qui vous contactera dans les prochaines minutes avec tous les dÃ©tails."

## Format de rÃ©ponse attendu

RÃ©ponds toujours en moins de 3 phrases. Sois direct, humain, utile.
Si needs_human est vrai, termine par une phrase qui rassure le contact qu'un humain va le contacter."""


def _openai_reply(message: str, api_key: str) -> dict | None:
    """Call OpenAI GPT to generate a contextual reply about Challenge Amazon FBA."""
    try:
        import httpx

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": 250,
                    "temperature": 0.35,
                },
            )
            resp.raise_for_status()
            reply_text = resp.json()["choices"][0]["message"]["content"].strip()

            # Detect human escalation signals in the AI reply itself
            _escalation_signals = [
                "conseiller", "transmets", "contactera", "Ã©quipe", "rappelÃ©",
                "needs_human", "humain",
            ]
            # Also detect strong purchase-intent signals from the original message
            _purchase_signals = [
                "je suis intÃ©ressÃ©", "comment aller plus loin", "je veux rejoindre",
                "je veux m'inscrire", "comment faire pour", "envoie-moi les dÃ©tails",
            ]
            needs_human = (
                any(w in reply_text.lower() for w in _escalation_signals)
                or any(w in message.lower() for w in _purchase_signals)
                or message.strip().lower() in {"oui", "yes", "oui!", "oui."}
            )

            return {
                "reply": reply_text,
                "needs_human": needs_human,
                "intent": "ai_generated",
            }
    except Exception:
        return None


_SAFE_OPENAI_KEYWORDS = {
    "challenge",
    "live",
    "session",
    "sessions",
    "whatsapp",
    "groupe",
    "lien",
    "horaire",
    "heure",
    "commence",
    "participation",
    "comment ca marche",
    "c est quoi le challenge",
}


def _looks_like_safe_challenge_question(message: str) -> bool:
    lowered = _normalize_text(message)
    return any(keyword in lowered for keyword in _SAFE_OPENAI_KEYWORDS)


def _clarification_reply() -> dict:
    return {
        "reply": "Je veux bien t'aider. Tu peux prÃ©ciser un peu ta question ?",
        "needs_human": False,
        "intent": "clarification_request",
    }


def build_reply(message: str) -> dict:
    text = _normalize_text(message)

    # 1. Fast local rules first (no API cost)
    local = _keyword_reply(text)
    if local:
        return local

    # 2. OpenAI if key is configured
    from shared.config.settings import settings
    if settings.openai_api_key and _looks_like_safe_challenge_question(message):
        ai = _openai_reply(message, settings.openai_api_key)
        if ai:
            return ai

    # 3. Default fallback: ask for clarification rather than improvising.
    return _clarification_reply()

