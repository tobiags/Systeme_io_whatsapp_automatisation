"""Local knowledge base for the WhatsApp bot.

Deterministic routing layer — checked BEFORE calling the LLM (OpenAI).

Design rules (from bot-guardrails-system.md):
1. KB lookup runs before any LLM call.
2. Exact message matches are checked first (short / fragile inputs like "1", "merci").
3. Keyword matching handles phrasing families.
4. Only add a rule for a pattern that appeared in a real conversation AND
   was handled badly by the generic fallback.
5. No rule should open a follow-up question unless explicitly approved.

Returns None when no rule matches — caller falls through to LLM.
"""
from __future__ import annotations

import unicodedata


# ── Normalisation ─────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Lowercase + remove accents + collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_text.split())


# ── Rule table ────────────────────────────────────────────────────────────────
# Each rule has:
#   intent        str        — machine-readable label
#   reply         str        — approved bot response
#   needs_human   bool       — whether to flag for closer follow-up
#   exact         set[str]   — normalised exact matches (optional)
#   keywords      list[str]  — if any keyword is a substring of the message (optional)

_RULES: list[dict] = [
    # ── Entry questionnaire: numeric choices ──────────────────────────────────
    {
        "intent": "entry_choice_beginner",
        "reply": (
            "Merci pour ton retour. Le challenge est justement prevu pour repartir "
            "sur des bases claires et t'aider a avancer pas a pas."
        ),
        "needs_human": False,
        "exact": {"1", "0", "zero", "de zero", "de 0", "a zero"},
    },
    {
        "intent": "entry_choice_started",
        "reply": (
            "Merci pour ton retour. Le challenge va justement t'aider a remettre "
            "les points essentiels dans le bon ordre pour avancer plus proprement."
        ),
        "needs_human": False,
        "exact": {"2"},
    },
    {
        "intent": "entry_choice_question",
        "reply": "Bien recu. Pose-moi ta question sur le challenge et je te reponds directement.",
        "needs_human": False,
        "exact": {"3"},
    },
    # ── Entry questionnaire: free-text mapping ────────────────────────────────
    {
        "intent": "entry_choice_beginner",
        "reply": (
            "Merci pour ton retour. Le challenge est justement prevu pour repartir "
            "sur des bases claires et t'aider a avancer pas a pas."
        ),
        "needs_human": False,
        "keywords": [
            "aucune experience", "je pars de zero", "je part de zero",
            "de zero", "debutant", "je commence", "je n ai pas encore commence",
            "jamais vendu",
        ],
    },
    {
        "intent": "entry_choice_started",
        "reply": (
            "Merci pour ton retour. Le challenge va t'aider a remettre "
            "les points essentiels dans le bon ordre."
        ),
        "needs_human": False,
        "keywords": [
            "j ai deja commence", "je vends deja", "je faisais la vente en ligne",
            "j ai une boutique", "je suis deja lance", "je vendais deja",
        ],
    },
    # ── Soft acknowledgements — never ask for clarification ───────────────────
    {
        "intent": "soft_acknowledgement",
        "reply": "Parfait. N'hesite pas si tu as une question avant le live.",
        "needs_human": False,
        "exact": {
            "ok", "okay", "ok merci", "merci", "super merci", "bien recu",
            "recu", "vu", "compris", "d accord", "daccord", "cool", "super",
            "parfait", "tres bien", "good", "noted", "ok super", "bonne journee",
        },
    },
    # ── FAQ: challenge schedule / overview ────────────────────────────────────
    {
        "intent": "faq_challenge_overview",
        "reply": (
            "Le challenge se deroule sur 3 sessions live sur StreamYard. "
            "Tu recevras le lien ici avant chaque session. "
            "L'objectif : comprendre comment lancer sur Amazon FBA pas a pas."
        ),
        "needs_human": False,
        "keywords": [
            "ca se passe comment", "comment se passe le challenge",
            "c est quoi le challenge", "comment ca marche", "comment fonctionne",
            "kesako", "c est quoi", "c'est comment",
        ],
    },
    # ── FAQ: StreamYard / link access ─────────────────────────────────────────
    {
        "intent": "faq_streamyard_access",
        "reply": (
            "Le live se suit directement via le lien StreamYard recu sur WhatsApp. "
            "Pas besoin de creer un compte — clique juste sur le lien. "
            "Pour la cohorte USA/Canada, l'heure indiquee est celle de Montreal."
        ),
        "needs_human": False,
        "keywords": [
            "lien streamyard", "lien du live", "ou se passe", "comment rejoindre le live",
            "application", "sur quel app", "fuseau horaire", "heure exacte",
            "je vois deux lien", "les deux liens",
        ],
    },
    # ── FAQ: replay ───────────────────────────────────────────────────────────
    {
        "intent": "faq_replay",
        "reply": (
            "Un replay sera partage apres chaque session. "
            "Tu recevras le lien directement ici sur WhatsApp."
        ),
        "needs_human": False,
        "keywords": [
            "replay", "revoir", "je peux revoir", "rediffusion",
            "j ai rate", "j'ai rate", "j ai manque", "si je rate",
        ],
    },
    # ── Explicit interest / purchase intent → escalate ────────────────────────
    {
        "intent": "explicit_interest",
        "reply": (
            "Super, je transmets ton message a l'equipe qui te recontacte "
            "directement avec les details !"
        ),
        "needs_human": True,
        "keywords": [
            "je veux acheter", "je veux rejoindre", "comment rejoindre le programme",
            "quel est le prix", "combien ca coute", "combien coute",
            "je suis pret", "on fait comment pour", "je veux m inscrire",
            "comment payer", "je veux payer",
        ],
    },
    # ── Time objection ────────────────────────────────────────────────────────
    {
        "intent": "time_objection",
        "reply": (
            "Je comprends. Les sessions sont courtes et les replays disponibles "
            "si tu ne peux pas etre la en direct. L'essentiel, c'est de ne pas "
            "passer a cote du contenu."
        ),
        "needs_human": False,
        "keywords": [
            "je serai au boulot", "j ai du travail", "je travaille ce soir",
            "pas disponible", "pas sur de pouvoir", "je ne pourrai pas",
            "temps", "manque de temps", "trop occupe",
        ],
    },
    # ── Beginner reassurance ──────────────────────────────────────────────────
    {
        "intent": "restricted_beginner_profile",
        "reply": (
            "C'est exactement pour ca que le challenge existe. "
            "On part des bases, pas besoin d'experience prealable."
        ),
        "needs_human": False,
        "keywords": [
            "je pars de zero", "je commence de zero", "je n ai pas d experience",
            "je ne connais rien", "je suis debutant", "novice", "je debute",
            "je part de rien",
        ],
    },
]


# ── Public lookup ─────────────────────────────────────────────────────────────

def kb_lookup(message: str) -> dict | None:
    """Return the first matching KB rule, or None if no rule matches.

    Checks exact matches first (O(1) set lookup), then keyword scan.
    Returns a dict with keys: intent, reply, needs_human.
    """
    normalised = _norm(message)

    for rule in _RULES:
        # 1. Exact match
        exact = rule.get("exact", set())
        if normalised in exact:
            return {"intent": rule["intent"], "reply": rule["reply"], "needs_human": rule["needs_human"]}

    for rule in _RULES:
        # 2. Keyword substring match
        for kw in rule.get("keywords", []):
            if kw in normalised:
                return {"intent": rule["intent"], "reply": rule["reply"], "needs_human": rule["needs_human"]}

    return None
