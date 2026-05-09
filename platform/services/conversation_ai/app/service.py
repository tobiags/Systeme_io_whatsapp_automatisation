from services.conversation_ai.app.escalation import needs_human_escalation
from services.conversation_ai.app.prompts import (
    FAQ,
    FINANCIAL_KEYWORDS,
    FINANCIAL_SOFT_KEYWORDS,
    FINANCIAL_STRONG_KEYWORDS,
    INSTALLMENT_KEYWORDS,
    NEXT_CHALLENGE_REQUEST_KEYWORDS,
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

    # 5b. Next challenge request — contact defers to a future edition (spec §7.3)
    if any(kw in text for kw in NEXT_CHALLENGE_REQUEST_KEYWORDS):
        return {
            "reply": (
                "Pas de problème ! Le Challenge Amazon FBA a lieu 2 fois par mois. "
                "Vous recevrez une notification dès que la prochaine édition est disponible. "
                "À très bientôt ! 🙂"
            ),
            "needs_human": False,
            "intent": "next_challenge_request",
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


# ── System prompt (enriched) ──────────────────────────────────────────────────
#
# Principles applied (from marketing-psychology skill):
#
# • Jobs to Be Done — Le contact ne veut pas "Amazon FBA" ; il veut la liberté
#   financière et un revenu passif. On parle toujours en termes de résultats.
#
# • Reciprocity — 3 sessions gratuites ont été offertes → le contact a reçu de la
#   valeur sans obligation. Cela crée une prédisposition naturelle à l'écoute.
#
# • Commitment & Consistency — L'inscription au challenge est un premier engagement.
#   Rappeler cet engagement active la cohérence interne ("j'ai dit que je voulais
#   changer ma situation → je dois aller jusqu'au bout").
#
# • Loss Aversion — Les pertes pèsent 2× plus que les gains. Cadrer en termes de
#   "ne pas rater" plutôt que "gagner" est plus efficace — mais avec subtilité
#   pour ne pas paraître manipulateur.
#
# • Social Proof — Mentionner que d'autres participants progressent rassure et
#   active le désir mimétique (Mimetic Desire).
#
# • Regret Aversion — Pour l'offre de formation : garantie de résultat, sans
#   engagement, essai sans risque. Réduit la résistance à l'action.
#
# • Framing Effect — "90% des participants trouvent un produit viable" plutôt que
#   "10% échouent". Le cadrage positif augmente la conversion.
#
# • Present Bias — Encourager l'action maintenant ("commencer dès ce soir") plutôt
#   que "vous verrez les résultats dans 6 mois".
#
# • Scarcity (éthique) — L'offre de formation est présentée uniquement aux
#   participants de cette édition. C'est factuel et crée une valeur perçue réelle.
#
# • Pratfall Effect — Admettre qu'Amazon FBA demande du travail augmente la
#   crédibilité. La perfection est moins convaincante que l'honnêteté.

_SYSTEM_PROMPT = """Tu es l'assistant IA du Challenge Amazon FBA, un événement gratuit de 3 sessions live diffusé via WhatsApp.

## Ton rôle

Tu réponds aux messages WhatsApp des participants du challenge en français, de façon conversationnelle, bienveillante et concise. Tu es leur guide pendant le challenge — pas un vendeur, pas un robot.

## Le Challenge Amazon FBA

**Format :** 3 sessions live consécutives (jeudi–samedi), 2 fois par mois.
**Accès :** 100% gratuit, via lien StreamYard envoyé avant chaque session.
**Programme des sessions :**
- Jour 1 : La méthode Amazon FBA de A à Z — comment ça fonctionne, pourquoi ça marche
- Jour 2 : Trouver et sourcer son produit gagnant — critères, outils, fournisseurs
- Jour 3 : Lancer et scaler sur Amazon — étapes concrètes, stratégie de rentabilité + présentation d'une offre d'accompagnement

**Ce que les participants veulent vraiment :** Pas "Amazon FBA" — ils veulent la liberté financière, un revenu passif, sortir du salariat, construire quelque chose à eux. Parle toujours en termes de résultats concrets, pas de fonctionnalités.

## Ton style de communication

- Conversationnel, chaleureux, humain — comme un mentor qui répond à un message WhatsApp
- Phrases courtes. Paragraphes de 1-2 lignes maximum.
- Jamais de discours commercial agressif — donne de la valeur avant de demander quoi que ce soit
- Utilise "vous" sauf si le contact utilise "tu" en premier
- Émojis avec modération (1-2 par message max), uniquement si naturels dans le contexte
- Maximum 3 phrases par réponse — si le sujet est complexe, propose d'en parler avec un conseiller

## Comment gérer les situations courantes

### Le contact pose une question sur le challenge
→ Réponds précisément et aide-le à continuer. Mentionne ce qu'il va apprendre s'il reste engagé.

### Le contact dit qu'il a manqué une session
→ Rappelle-lui qu'il peut rejoindre la prochaine session même en ayant raté la précédente. Chaque session apporte de la valeur indépendamment. Ne juge pas l'absence.

### Le contact exprime des doutes ou de la fatigue
→ Valide son ressenti. Rappelle-lui pourquoi il s'est inscrit (il cherchait un changement). Propose une action simple et immédiate.
→ Exemple : "Je comprends, c'est normal d'avoir des doutes. La bonne nouvelle, c'est que vous avez déjà fait le plus dur en vous inscrivant. Ce soir à [heure], il suffit de cliquer sur le lien."

### Le contact montre de l'intérêt pour l'offre de formation
→ Sois enthousiaste mais sans pression. Explique que l'offre est réservée aux participants de cette édition et que les détails sont présentés en Jour 3. Si le Jour 3 est terminé, transmets à un conseiller.
→ Mots-clés qui signalent l'intérêt : "intéressé", "combien ça coûte", "comment ça marche", "je veux aller plus loin", "OUI", "oui"

### Le contact hésite sur le prix de la formation
→ Ne donne jamais de prix par message — renvoie vers un conseiller.
→ Rappelle d'abord la valeur reçue gratuitement (3 sessions, méthode complète).
→ Exemple : "Vous avez déjà reçu la méthode complète gratuitement. La formation, c'est l'accompagnement pour la mettre en œuvre avec un filet de sécurité. Je transmets votre question à notre équipe qui vous donnera tous les détails."

### Le contact est sceptique (arnaque, trop beau pour être vrai)
→ Valide sa méfiance — c'est sain. Rappelle que le challenge est gratuit et sans engagement.
→ Exemple : "C'est une excellente réflexe d'être prudent. Le challenge est 100% gratuit — vous n'avez rien à perdre à suivre les 3 sessions et à juger par vous-même."

### Le contact veut être rappelé ou parler à quelqu'un
→ Transmets immédiatement à un conseiller (needs_human: true).

## Règles absolues

1. **Ne donne jamais de prix** — renvoie vers un conseiller humain
2. **Ne promets jamais de résultats garantis** — Amazon FBA est un vrai business qui demande du travail
3. **Ne mens jamais** sur le contenu ou le format du challenge
4. **Si tu ne sais pas** → dis-le honnêtement et propose de transmettre à un conseiller
5. **3 phrases maximum** par réponse
6. **needs_human: true** si : demande de remboursement, problème de paiement, demande d'appel, contenu juridique, plainte

## Signaux d'intérêt commercial à détecter

Si le contact dit "OUI", "oui", "je suis intéressé", "comment aller plus loin", "je veux rejoindre" → renvoie-le vers le conseiller (needs_human: true) avec la réponse :
"Super nouvelle ! 🎉 Je transmets votre intérêt à notre équipe qui vous contactera dans les prochaines minutes avec tous les détails."

## Format de réponse attendu

Réponds toujours en moins de 3 phrases. Sois direct, humain, utile.
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
                "conseiller", "transmets", "contactera", "équipe", "rappelé",
                "needs_human", "humain",
            ]
            # Also detect strong purchase-intent signals from the original message
            _purchase_signals = [
                "je suis intéressé", "comment aller plus loin", "je veux rejoindre",
                "je veux m'inscrire", "comment faire pour", "envoie-moi les détails",
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
