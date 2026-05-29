"""Safety guardrails — checked BEFORE calling Claude.

Critical patterns trigger immediate human escalation (no AI reply).
"""

_CRITICAL_PATTERNS = [
    # Payment & billing
    "remboursement", "rembourse", "refund", "paiement echoue", "carte refusée",
    "prélèvement", "prelevé", "débit", "double facturation", "arnaque", "fraude",
    # Legal & threats
    "avocat", "tribunal", "plainte", "signalement", "juridique", "procès",
    "autorité", "gendarmerie", "police",
    # Strong negative signals
    "arnaquer", "mensonge", "menteur", "escroc", "honte",
]

_INTEREST_SIGNALS = [
    "intéressé", "interesse", "je veux", "j'achète", "j'achete",
    "comment rejoindre", "comment s'inscrire", "comment participer",
    "je suis prêt", "on fait comment", "c'est combien", "quel prix", "le prix",
    "payer", "régler",
]

_QUESTION_SIGNALS = [
    "?", "comment", "pourquoi", "quand", "où", "qui", "quel", "quelle",
    "est-ce que", "est ce que", "c'est quoi", "qu'est-ce",
]


def is_critical(text: str) -> bool:
    """Returns True if the message requires immediate human escalation."""
    lowered = text.lower()
    return any(p in lowered for p in _CRITICAL_PATTERNS)


def has_offer_interest(text: str) -> bool:
    lowered = text.lower()
    return any(s in lowered for s in _INTEREST_SIGNALS)


def has_question(text: str) -> bool:
    lowered = text.lower()
    return any(s in lowered for s in _QUESTION_SIGNALS)
