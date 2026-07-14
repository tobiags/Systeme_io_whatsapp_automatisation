import logging
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

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

logger = logging.getLogger(__name__)


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

# ── Bot auto-reply signatures ─────────────────────────────────────────────────
# Some contacts have WhatsApp business bots that reply automatically.
# We detect these and silently ignore them — no reply sent, no human flag.
_BOT_AUTO_REPLY_SIGNATURES = [
    "merci de contacter",
    "nous ne sommes pas disponibles pour repondre",
    "nous vous repondrons des que possible",
    "dites-nous en quoi nous pouvons vous aider",
    "dites nous en quoi nous pouvons vous aider",
    "please let us know how we can help",
    "you just triggered an automation rule",
    "thank you for contacting",
    "this is an automated message",
    "vous avez declenche une regle d automatisation",
    "rezo pwofesyonèl lakay",
    "koman nou kapab edew",
    "merci d avoir contacte",
    "nous ne sommes pas disponible",
    "mesi paske w kontakte",
    "pou mwen svp",  # Creole business bot pattern
]


def _is_bot_auto_reply(normalized_text: str) -> bool:
    """Detect WhatsApp business bot auto-responses that should be silently ignored."""
    return any(sig in normalized_text for sig in _BOT_AUTO_REPLY_SIGNATURES)

_SELF_SERVICE_FAQ_INTENTS = {
    "faq_start_time",
    "faq_challenge_overview",
    "faq_whatsapp_group_join",
}

_ENTRY_QUESTIONNAIRE_INTENTS = {
    "entry_choice_beginner",
    "entry_choice_started",
    "entry_choice_question",
}

# ── Language detection ────────────────────────────────────────────────────────

# Haitian Creole lexical markers (common Creole words / phonetics distinct from French)
_CREOLE_MARKERS = [
    "mwen ", " nan ", " ak ", " pou ", " li ", " sa ", " yo ", " nou ",
    " pa ", " gen ", " la ", " ou ", "bonswa", "mesi ", "mèsi",
    "eskize", "paske", "kounya", "mezanmi", "depi ", "anpil", "ayiti",
    "kreyol", "kreyòl", "ayisyen", "paka ", "bezwen", "reponn",
    "pwofesyonel", "deske", "deskew",
]

# English lexical markers
_ENGLISH_MARKERS = [
    "i want", "i need", "i don't", "i didn't", "i haven't", "i wasn't",
    "how do i", "how does", "can you", "please ", "thank you", "hello",
    "hi there", "good morning", "good evening", "is the", "are you",
    "what is", "where is", "when is", "who are", "i am ", "i'm ",
    "you are", "you're", "it is ", "it's ", "the training", "the challenge",
    "is it free", "is this",
]


def _detect_language(text: str) -> str:
    """Detect message language: 'fr' (default), 'en' (English), 'ht' (Haitian Creole).

    Uses a simple lexical scoring approach — no external library, fast enough for
    every inbound webhook. Haitian Creole takes priority when markers score higher,
    since Creole messages often contain French loanwords that inflate the FR score.
    """
    lower = " " + text.lower() + " "

    ht_score = sum(1 for marker in _CREOLE_MARKERS if marker in lower)
    en_score = sum(1 for marker in _ENGLISH_MARKERS if marker in lower)

    # Require at least 2 markers to avoid false positives on short messages
    if ht_score >= 2 and ht_score >= en_score:
        return "ht"
    if en_score >= 2 and en_score > ht_score:
        return "en"

    # Single very strong Creole signals
    if any(s in lower for s in ["mwen bezwen", "sa a ", "ki jan ", "kouman ", "ki kote "]):
        return "ht"

    # Single very strong English signals
    if any(s in lower for s in ["i want to", "is the training", "are you available", "who are you"]):
        return "en"

    return "fr"


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


def _kb_rule_reply(rule: dict, language: str = "fr") -> str:
    """Pick the reply string for a KB rule in the right language.

    Falls back to French if the requested translation is not defined.
    """
    if language == "en":
        return rule.get("reply_en") or rule.get("reply", "")
    if language == "ht":
        return rule.get("reply_ht") or rule.get("reply", "")
    return rule.get("reply", "")


def _knowledge_base_reply(normalized_text: str, language: str = "fr") -> dict | None:
    for rule in KB_GUARDRAIL_RULES:
        if normalized_text in rule.get("exact_messages", set()):
            payload = {
                "reply": _kb_rule_reply(rule, language),
                "needs_human": rule["needs_human"],
                "intent": rule["intent"],
            }
            entry_state = _entry_choice_script_state(rule["intent"])
            if entry_state:
                payload["script_state"] = entry_state
            if "script_state" in rule:
                payload["script_state"] = rule["script_state"]
            return payload

        if _matches_any_phrase(
            normalized_text,
            rule.get("keywords", []),
            threshold=rule.get("threshold", 0.9),
        ):
            payload = {
                "reply": _kb_rule_reply(rule, language),
                "needs_human": rule["needs_human"],
                "intent": rule["intent"],
            }
            entry_state = _entry_choice_script_state(rule["intent"])
            if entry_state:
                payload["script_state"] = entry_state
            if "script_state" in rule:
                payload["script_state"] = rule["script_state"]
            return payload
    return None


def _entry_choice_script_state(intent: str) -> dict | None:
    if intent not in _ENTRY_QUESTIONNAIRE_INTENTS:
        return None
    return {
        "flow": "entry_questionnaire",
        "stage": "choice_captured",
        "selected_intent": intent,
        "rephrase_count": 0,
    }


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


def _keyword_reply(text: str, language: str = "fr") -> dict | None:
    """
    Fast local reply using FAQ, signal-level routing and a few guarded topic handlers.
    """
    normalized_text = _normalize_text(text)

    if needs_human_escalation(normalized_text):
        _escalation_replies = {
            "en": "I'm passing your request to our team — someone will get back to you shortly.",
            "ht": "M ap transmèt demann ou bay ekip nou an — yon moun ap tounen jwenn ou byento.",
            "fr": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
        }
        return {
            "reply": _escalation_replies.get(language, _escalation_replies["fr"]),
            "needs_human": True,
            "intent": "human_escalation",
        }

    knowledge = _knowledge_base_reply(normalized_text, language)
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


def _critical_guardrail_reply(text: str) -> dict | None:
    """Local hard stops that must not depend on model generation."""
    normalized_text = _normalize_text(text)

    if needs_human_escalation(normalized_text):
        return {
            "reply": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
            "needs_human": True,
            "intent": "human_escalation",
        }

    if _matches_any_phrase(normalized_text, _ESCALATE_NOW_PHRASES, threshold=0.88):
        return {
            "reply": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
            "needs_human": True,
            "intent": "human_escalation",
        }

    for phrases, intent in [
        (PAYMENT_FAILURE_KEYWORDS, "payment_failure_followup_needed"),
        (INSTALLMENT_KEYWORDS, "installment_plan_request"),
        (SCEPTIC_KEYWORDS, "skeptic_trust_objection"),
        (FINANCIAL_STRONG_KEYWORDS, "objection_financial_strong"),
        (FINANCIAL_SOFT_KEYWORDS, "objection_financial_soft"),
        (FINANCIAL_KEYWORDS, "financial_objection"),
    ]:
        if _matches_any_phrase(normalized_text, phrases, threshold=0.9):
            return {
                "reply": "Je transmets ta demande a l'equipe.",
                "needs_human": True,
                "intent": intent,
            }
    return None


@lru_cache(maxsize=1)
def _load_best_skill() -> str:
    path = Path(__file__).with_name("best_skill.md")
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""

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

### Le contact dit qu’il a manquÃ© une session
â†’ Rappelle-lui qu’il peut rejoindre la prochaine session mÃªme en ayant ratÃ© la prÃ©cÃ©dente. Chaque session apporte de la valeur indÃ©pendamment. Ne juge pas l’absence. Si on demande un replay, dis que le replay est disponible aprÃ¨s la fin du challenge.

### Le contact a un problÃ¨me technique (lien, connexion, email non reconnu)
â†’ Guide en 3 Ã©tapes simples : (1) cliquer sur le lien WhatsApp, (2) s’inscrire avec un email, (3) Ã  19h recliquÃ©r sur ce mÃªme lien. Aucune application Ã  tÃ©lÃ©charger. Si le problÃ¨me persiste, demande l’email.

### Le contact demande si c’est accessible depuis son pays (HaÃ¯ti, Afrique, etc.)
â†’ Confirme que le challenge est 100% en ligne, accessible depuis n’importe quel pays.

### Le contact mentionne une formation personnalisÃ©e ou un accompagnement individuel
â†’ Transmets immÃ©diatement Ã  un conseiller (needs_human: true) avec la rÃ©ponse :
"Super ! Je transmets ton intÃ©rÃªt Ã  notre Ã©quipe qui te contactera rapidement avec tous les dÃ©tails ðŸŽ‰"

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

## Gestion des langues

Tu peux recevoir des messages en francais, en anglais ou en creole haitien (Kreyol).
Le contexte indique "langue_detectee" — utilise TOUJOURS cette langue pour repondre.

Francais -> reponds en francais
English -> reply in English
Kreyol -> reponn an kreyol ayisyen

Si le message est melange, utilise la langue dominante.

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
Si needs_human est vrai, termine par une phrase qui rassure le contact qu'un humain va le contacter.

## Utilisation des liens disponibles

Le contexte peut contenir une section "Liens disponibles pour cette edition". Utilise ces liens directement dans ta reponse quand ils sont pertinents.

Regles :
- Si on demande un replay (session manquee, video enregistree, rediffusion) -> inclure le(s) lien(s) Replay Jour X disponibles. Si aucun replay n'est disponible, dire qu'il sera envoye apres la fin du challenge.
- Si on demande le lien du live (connexion, acces, impossible de rejoindre) -> inclure le lien Live Jour X du jour concerne.
- Ne jamais partager le lien paiement de ta propre initiative.
- Ne jamais inventer de liens -- utilise uniquement les liens presents dans le contexte."""



def _build_openai_system_prompt() -> str:
    best_skill = _load_best_skill()
    if not best_skill:
        return _SYSTEM_PROMPT
    return f"{_SYSTEM_PROMPT}\n\n## Skill metier optimisee\n\n{best_skill}"


def _format_context_for_openai(context: dict | None) -> str:
    if not context:
        return ""
    lines = ["Contexte court disponible :"]
    for key in [
        "contact_first_name",
        "cohort",
        "edition_key",
        "edition_date",
        "current_step",
        "last_outbound_template",
        "last_outbound_status",
        "last_outbound_variables",
        "last_ai_reply",
        "last_ai_intent",
    ]:
        value = context.get(key)
        if value:
            lines.append(f"- {key}: {value}")

    # Language detected for this message — tell the model which language to use.
    lang = context.get("detected_language", "fr")
    _lang_labels = {"fr": "Français", "en": "English", "ht": "Créole haïtien (Kreyòl)"}
    lines.append(f"- langue_detectee: {_lang_labels.get(lang, lang)} — REPONDS DANS CETTE LANGUE")

    # Parse active_live_links into a readable block so the model can quote real URLs.
    # Format: "live_day1=URL; live_day2=URL; replay_day1=URL; payment=URL; ..."
    raw_links = context.get("active_live_links", "")
    if raw_links:
        lines.append("Liens disponibles pour cette edition :")
        for part in raw_links.split(";"):
            part = part.strip()
            if "=" in part:
                label, url = part.split("=", 1)
                label_map = {
                    "live_day1": "Live Jour 1",
                    "live_day2": "Live Jour 2",
                    "live_day3": "Live Jour 3",
                    "replay_day1": "Replay Jour 1",
                    "replay_day2": "Replay Jour 2",
                    "replay_day3": "Replay Jour 3",
                    "payment": "Lien paiement",
                    "closer": "Reserv. appel closer",
                }
                readable = label_map.get(label.strip(), label.strip())
                lines.append(f"  {readable}: {url.strip()}")

    return "\n".join(lines)


def _openai_reply(message: str, api_key: str, context: dict | None = None) -> dict | None:
    """Call OpenAI GPT to generate a contextual reply about Challenge Amazon FBA."""
    try:
        import httpx

        with httpx.Client(timeout=8.0) as client:
            context_text = _format_context_for_openai(context)
            user_content = message if not context_text else f"{context_text}\n\nMessage participant : {message}"
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": _build_openai_system_prompt()},
                        {"role": "user", "content": user_content},
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
    except Exception as exc:
        logger.warning("OpenAI reply generation failed: %s", exc)
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


def _has_known_contact_context(context: dict | None) -> bool:
    return bool(context and context.get("contact_id"))


def _clarification_reply(language: str = "fr") -> dict:
    _clarification_replies = {
        "en": "I'd love to help. Could you be a bit more specific?",
        "ht": "M ta renmen ede ou. Eske ou ka esplike pi plis?",
        "fr": "Je veux bien t'aider. Tu peux preciser un peu ta question ?",
    }
    return {
        "reply": _clarification_replies.get(language, _clarification_replies["fr"]),
        "needs_human": False,
        "intent": "clarification_request",
    }


def build_reply(message: str, context: dict | None = None) -> dict:
    text = _normalize_text(message)

    if not text:
        return {
            "reply": "",
            "needs_human": False,
            "intent": "acknowledgement_no_reply",
            "send_reply": False,
        }

    # 0. Bot auto-reply detection — silently ignore business automation responses.
    if _is_bot_auto_reply(text):
        return {
            "reply": "",
            "needs_human": False,
            "intent": "bot_auto_reply_ignored",
            "send_reply": False,
        }

    # Detect language early — used by KB rules, clarification, and OpenAI context.
    language = _detect_language(message)
    # Inject language into context so OpenAI can read it.
    if context is not None:
        context = {**context, "detected_language": language}

    # 1. Critical local guardrails first. These are hard stops, not style rules.
    critical = _critical_guardrail_reply(text)
    if critical:
        return critical

    from shared.config.settings import settings

    # 2. For known contacts, let OpenAI use the skill + short memory before
    # broad keyword fallbacks. This is what makes the bot less robotic.
    if settings.openai_api_key and _has_known_contact_context(context):
        ai = _openai_reply(message, settings.openai_api_key, context=context)
        if ai:
            return ai

    # 3. Deterministic local rules for no-key/dev and known safe patterns.
    local = _keyword_reply(text, language=language)
    if local:
        return local

    # 4. Unknown contacts still get OpenAI only for clearly challenge-scoped text.
    if settings.openai_api_key and _looks_like_safe_challenge_question(message):
        ai = _openai_reply(message, settings.openai_api_key, context=context)
        if ai:
            return ai

    # 5. Default fallback: ask for clarification rather than improvising.
    return _clarification_reply(language=language)

