"""Local guardrails knowledge base for recurring WhatsApp lead messages.

This module is intentionally simple:
- one ordered list of rules
- exact message matches first
- approximate keyword matching second

The goal is to capture recurring production phrasing before the generic
routing logic or LLM fallback gets a chance to drift.

How to extend safely:
1. Add a new rule only for a repeated real-world pattern.
2. Keep the reply short and aligned with the client guardrails.
3. Prefer exact_messages for short inputs like "0" or "merci".
4. Use keywords for families of phrasing.
5. Add or update a regression test in `platform/tests/e2e/`.
"""

from __future__ import annotations

from typing import TypedDict


class KBRule(TypedDict, total=False):
    intent: str
    reply: str
    needs_human: bool
    exact_messages: set[str]
    keywords: list[str]
    threshold: float
    script_state: dict


KB_GUARDRAIL_RULES: list[KBRule] = [
    # Level: restricted beginner declarations seen in production.
    {
        "intent": "restricted_beginner_profile",
        "reply": (
            "Merci pour ton retour. Ce point sera justement aborde pendant le challenge, "
            "de facon claire et concrete."
        ),
        "needs_human": False,
        "exact_messages": {
            "0",
            "zero",
            "de 0",
            "de zero",
            "a zero",
        },
        "keywords": [
            "de zero",
            "de zeroo",
            "je part de zero",
            "je pars de zero",
            "je commence de zero",
            "je repars de zero",
            "je suis debutant",
        ],
        "threshold": 0.88,
    },
    # Level: explicit interest; allowed to ask one follow-up question.
    {
        "intent": "interest_followup_objective",
        "reply": "Qu'est-ce que tu cherches surtout a obtenir avec ce challenge aujourd'hui ?",
        "needs_human": False,
        "script_state": {"next_stage": "awaiting_interest_followup", "topic": "objective"},
        "keywords": [
            "j aimerais apprendre",
            "je veux apprendre",
            "j aimerais en savoir plus",
            "je veux en savoir plus",
            "je veux participer",
            "ca m interesse",
            "je suis interesse",
            "j aimerais bien creer une boutique en ligne",
            "creer une boutique en ligne",
            "creer un business en ligne",
        ],
        "threshold": 0.88,
    },
    # Level: FAQ about challenge structure.
    {
        "intent": "faq_challenge_overview",
        "reply": (
            "Le challenge se passe sur 3 sessions live gratuites. "
            "Tu recois les liens WhatsApp avant chaque session, puis on avance pas a pas pendant le parcours."
        ),
        "needs_human": False,
        "keywords": [
            "ca se passe comment le challenge",
            "comment se passe le challenge",
            "comment fonctionne le challenge",
            "comment marche le challenge",
        ],
        "threshold": 0.88,
    },
    # Level: practical availability statement; acknowledge and keep it useful.
    {
        "intent": "availability_support",
        "reply": (
            "Pas de souci. Si tu es pris par le boulot, connecte-toi des que tu peux "
            "et garde bien le lien du live sous la main."
        ),
        "needs_human": False,
        "keywords": [
            "je serais au boulot",
            "je serai au boulot",
            "je serais au travail",
            "je serai au travail",
            "ne pas rater le live",
            "pas rater le live",
            "au boulot a cette heure",
            "au travail a cette heure",
        ],
        "threshold": 0.88,
    },
    # Level: soft acknowledgements that should not trigger clarification loops.
    {
        "intent": "soft_open_invitation",
        "reply": "N'hesite pas si t'as une question sur le challenge.",
        "needs_human": False,
        "keywords": [
            "merci alban",
            "merci beaucoup",
            "super merci",
            "merci pour ta reponse",
            "c est aussi un plaisir pour moi",
            "bien recu",
            "merci",
            "super",
        ],
        "threshold": 0.92,
    },
]
