KB_GUARDRAIL_RULES = [
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
            "de zero ",
            "je part de zero",
            "je pars de zero",
            "je commence de zero",
            "je repars de zero",
            "je suis debutant",
        ],
        "threshold": 0.88,
    },
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
    {
        "intent": "soft_open_invitation",
        "reply": "N'hesite pas si t'as une question sur le challenge 😊",
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
