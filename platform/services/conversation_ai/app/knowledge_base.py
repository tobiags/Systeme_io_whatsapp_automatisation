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
    # Entry questionnaire numeric choices.
    {
        "intent": "entry_choice_beginner",
        "reply": (
            "Merci pour ton retour. Le challenge est justement prevu pour repartir "
            "sur des bases claires et t'aider a avancer pas a pas."
        ),
        "needs_human": False,
        "exact_messages": {"1", "0", "zero", "de 0", "de zero", "a zero"},
    },
    {
        "intent": "entry_choice_started",
        "reply": (
            "Merci pour ton retour. Le challenge va justement t'aider a remettre "
            "les points essentiels dans le bon ordre pour avancer plus proprement."
        ),
        "needs_human": False,
        "exact_messages": {"2"},
    },
    {
        "intent": "entry_choice_question",
        "reply": "Bien recu. Pose-moi ta question sur le challenge et je te reponds directement.",
        "needs_human": False,
        "exact_messages": {"3"},
    },
    # Entry questionnaire free-text mapping.
    {
        "intent": "entry_choice_beginner",
        "reply": (
            "Merci pour ton retour. Le challenge est justement prevu pour repartir "
            "sur des bases claires et t'aider a avancer pas a pas."
        ),
        "needs_human": False,
        "keywords": [
            "aucune experience",
            "aucune experience en vente en ligne",
            "je pars de zero",
            "je part de zero",
            "de zero",
            "de zer0",
            "debutant",
            "je commence",
            "je comence de zero",
            "je n ai pas encore commence",
        ],
        "threshold": 0.88,
    },
    {
        "intent": "entry_choice_started",
        "reply": (
            "Merci pour ton retour. Le challenge va justement t'aider a remettre "
            "les points essentiels dans le bon ordre pour avancer plus proprement."
        ),
        "needs_human": False,
        "keywords": [
            "j ai deja commence",
            "je vends deja",
            "je faisais la vente en ligne",
            "j ai une boutique",
            "je suis deja lance",
            "je vendais deja",
            "je suis en adaptation",
        ],
        "threshold": 0.88,
    },
    # Keep this before the broad "lien" entry-choice rule.
    {
        "intent": "live_access_time_help",
        "reply": (
            "Le live se suit directement via le lien StreamYard recu sur WhatsApp. "
            "S'il y a deux liens, garde le dernier lien recu : c'est celui de la prochaine session. "
            "Pour la cohorte USA/Canada, l'heure indiquee correspond a l'heure de Montreal."
        ),
        "needs_human": False,
        "keywords": [
            "je vois deux lien",
            "je vois deux liens",
            "les deux seront utilises",
            "sur quel application",
            "sur quelle application",
            "quelle application",
            "heure haitienne",
            "fuseau horaire",
            "heure exacte du live",
            "j ai vu un message me disant que j ai manque le premier live",
            "j esperais rejoindre le live a 19hr",
        ],
        "threshold": 0.84,
    },
    {
        "intent": "entry_choice_question",
        "reply": "Bien recu. Pose-moi ta question sur le challenge et je te reponds directement.",
        "needs_human": False,
        "keywords": [
            "comment ca marche",
            "c est quoi le challenge",
            "horaire",
            "lien",
            "comment participer",
            "comment se passe le challenge",
        ],
        "threshold": 0.88,
    },
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
    # Level: live access / timing confusion observed after overlapping reminders.
    {
        "intent": "live_access_time_help",
        "reply": (
            "Le live se suit directement via le lien StreamYard recu sur WhatsApp. "
            "S'il y a deux liens, garde le dernier lien recu : c'est celui de la prochaine session. "
            "Pour la cohorte USA/Canada, l'heure indiquee correspond a l'heure de Montreal."
        ),
        "needs_human": False,
        "keywords": [
            "je vois deux lien",
            "je vois deux liens",
            "les deux seront utilises",
            "sur quel application",
            "sur quelle application",
            "quelle application",
            "heure haitienne",
            "fuseau horaire",
            "heure exacte du live",
            "j ai vu un message me disant que j ai manque le premier live",
            "j esperais rejoindre le live a 19hr",
        ],
        "threshold": 0.84,
    },
    {
        "intent": "live_participation_confirmed",
        "reply": (
            "Parfait, c'est note. Garde simplement le lien du live sous la main "
            "et connecte-toi quelques minutes avant l'heure prevue."
        ),
        "needs_human": False,
        "keywords": [
            "j y serai",
            "je serai present",
            "je serais present",
            "je serrai present",
            "j ai serait present",
            "pour ma participation cet apres midi",
            "j attends le debut du webinaire",
            "je disais que j attends le debut du webinaire",
            "c est note",
            "cest note",
        ],
        "threshold": 0.84,
    },
    {
        "intent": "beginner_reassurance_no_question",
        "reply": (
            "C'est justement pour ca que le challenge est utile. "
            "Tu n'as pas besoin de connaitre l'e-commerce avant de commencer : suis les lives dans l'ordre, "
            "et les bases seront reprises simplement."
        ),
        "needs_human": False,
        "keywords": [
            "c est ma premiere fois",
            "je ne connais rien en e commerce",
            "je connais rien en e commerce",
            "je ne connais rien",
            "je n ai pas de questions parce que je connais rien",
            "moi j ai ne pas des questions parce que j ai connais rien",
            "avant tout je voudrais entendre et voir",
            "je voudrais entendre et voir ce que ca passe",
        ],
        "threshold": 0.84,
    },
    {
        "intent": "challenge_participation_requirements",
        "reply": (
            "Pour participer, il suffit de garder le lien du live, etre connecte a l'heure indiquee "
            "et suivre les explications. Les principes du challenge seront presentes pendant les 3 sessions : "
            "comprendre Amazon FBA, trouver un produit, puis voir les etapes de lancement."
        ),
        "needs_human": False,
        "keywords": [
            "quels seront les mesures necessaires pour participer",
            "mesures necessaires pour participer",
            "quelles sont les choses et principe",
            "choses et principe du challenge",
            "principe qui fait parti du challenge",
        ],
        "threshold": 0.84,
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
