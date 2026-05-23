# ── FAQ ──────────────────────────────────────────────────────────────────────
# Each entry: keyword (lowercased) → (answer, intent_id)
# Intent IDs match the spec: faq_whatsapp_group_join, faq_email_missing, etc.

FAQ: dict[str, tuple[str, str]] = {
    # Quand ça commence
    "quand ca commence": (
        "Le Challenge Amazon FBA se déroule du jeudi au samedi selon votre zone horaire. "
        "Vous recevrez le lien de connexion avant chaque session.",
        "faq_start_time",
    ),
    "quand est-ce que cela commence": (
        "Le Challenge Amazon FBA se déroule du jeudi au samedi selon votre zone horaire. "
        "Vous recevrez le lien de connexion avant chaque session.",
        "faq_start_time",
    ),
    "quand commence": (
        "Le Challenge Amazon FBA se déroule du jeudi au samedi selon votre zone horaire.",
        "faq_start_time",
    ),

    # Groupe WhatsApp
    "comment rejoindre le groupe whatsapp": (
        "Le lien du groupe WhatsApp vous est envoyé dans la séquence de bienvenue après votre inscription. "
        "Vérifiez vos messages WhatsApp ou vos emails.",
        "faq_whatsapp_group_join",
    ),
    "rejoindre le groupe": (
        "Le lien du groupe WhatsApp vous a été envoyé par message après votre inscription.",
        "faq_whatsapp_group_join",
    ),
    "lien du groupe": (
        "Le lien du groupe WhatsApp vous a été envoyé par message après votre inscription.",
        "faq_whatsapp_group_join",
    ),

    # Email manquant
    "je me suis inscrit mais je n'ai pas recu d'email": (
        "Vérifiez vos spams et courriers indésirables. "
        "Si vous ne trouvez toujours pas, répondez ici avec votre adresse email et nous vérifierons.",
        "faq_email_missing",
    ),
    "pas recu d'email": (
        "Vérifiez vos spams. Si le problème persiste, répondez ici avec votre adresse email.",
        "faq_email_missing",
    ),
    "pas recu le lien": (
        "Le lien de live est envoyé par email et WhatsApp avant chaque session. "
        "Vérifiez vos spams ou répondez ici pour que nous vérifiions.",
        "faq_email_missing",
    ),

    # Prix de la formation
    "combien coute la formation": (
        "Le Challenge Amazon FBA est entièrement gratuit. "
        "Les détails de la formation complète sont présentés pendant et à la fin du challenge.",
        "faq_offer_price",
    ),
    "combien ca coute": (
        "Le challenge est gratuit. Les détails de l'offre de formation sont présentés pendant le parcours.",
        "faq_offer_price",
    ),
    "c'est gratuit": (
        "Oui, le Challenge Amazon FBA est 100% gratuit. "
        "Une offre de formation est présentée à la fin pour ceux qui souhaitent aller plus loin.",
        "faq_offer_price",
    ),

    # Prochain challenge
    "quand est-ce que vous referez un nouveau challenge": (
        "Le Challenge Amazon FBA a lieu 2 fois par mois, du jeudi au samedi. "
        "Restez abonné à nos messages pour être informé des prochaines dates.",
        "faq_next_challenge_date",
    ),
    "prochain challenge": (
        "Le prochain Challenge Amazon FBA aura lieu prochainement. "
        "Vous serez notifié par WhatsApp dès que les inscriptions sont ouvertes.",
        "faq_next_challenge_date",
    ),
    "prochaine edition": (
        "Le Challenge Amazon FBA a lieu 2 fois par mois. "
        "Vous recevrez un message dès que la prochaine édition est disponible.",
        "faq_next_challenge_date",
    ),
}

# —— Qualification / niveau de départ ————————————————————————————————————————————
# Used right after welcome when a lead answers with their starting level.
BEGINNER_PROFILE_KEYWORDS = [
    "je pars de zero",
    "je pars de zéro",
    "je repars de zero",
    "je repars de zéro",
    "je part de zero",
    "je part de zéro",
    "alors oui je pars de zéro",
    "bonjour je pars de zero",
    "bonjour je pars de zéro",
    "je suis debutant",
    "je suis débutant",
    "debutant",
    "débutant",
    "je n'ai pas encore commence",
    "je n'ai pas encore commencé",
    "je ne pas encore je vais partir à zéro",
    "je vais partir de zero",
    "je vais partir de zéro",
    "de 0",
    "a zero",
    "à zéro",
    "zero",
    "zéro",
    "je voudrais commencer",
    "je veux commencer",
    "je veux debuter",
    "je veux débuter",
]

STARTED_PROFILE_KEYWORDS = [
    "j'ai deja commence",
    "j'ai déjà commencé",
    "j'ai deja vendu",
    "j'ai déjà vendu",
    "j'ai commence",
    "j'ai commencé",
    "je vends deja",
    "je vends déjà",
    "je vends en ligne",
    "j'ai un peu d'experience",
    "j'ai un peu d'expérience",
    "j'ai de l'experience",
    "j'ai de l'expérience",
    "je connais deja amazon fba",
    "je connais déjà amazon fba",
]

TIME_OBJECTION_KEYWORDS = [
    "pas le temps",
    "je manque de temps",
    "le temps",
    "je n'ai pas le temps",
    "je n ai pas le temps",
    "trop occupe",
    "trop occupé",
]

PRODUCT_CHOICE_KEYWORDS = [
    "choix du produit",
    "je ne sais pas quoi vendre",
    "je sais pas quoi vendre",
    "quel produit",
    "quel type de produit",
    "trouver un produit",
    "produit gagnant",
]

# ── Financial objection classification ───────────────────────────────────────
# Each group maps to a specific intent and reply strategy.

# Soft: general budget concern without specific action signal
FINANCIAL_SOFT_KEYWORDS = [
    "trop cher", "c'est cher", "pas le budget", "pas les moyens",
    "je n'ai pas le budget", "manque d'argent", "coût", "coute",
    "je veux réfléchir", "pas sûr de pouvoir investir",
]

# Strong: explicit refusal or repeated objection with no engagement
FINANCIAL_STRONG_KEYWORDS = [
    "impossible pour moi", "hors de prix", "jamais à ce prix",
    "trop risqué", "je ne peux vraiment pas",
]

# Installment / payment plan request
INSTALLMENT_KEYWORDS = [
    "payer en plusieurs fois", "payer en 2 fois", "payer en 3 fois",
    "payer en 10 fois", "plan de paiement", "facilités de paiement",
    "mensualités", "échelonner",
]

# Payment attempt failure
PAYMENT_FAILURE_KEYWORDS = [
    "essayé de payer", "essayé de payer mais", "paiement refusé",
    "fonds insuffisants", "pas assez sur mon compte", "carte refusée",
    "paiement échoué", "j'ai pas pu payer",
]

# Sceptic / trust objection
SCEPTIC_KEYWORDS = [
    "j'ai peur de perdre", "arnaque", "fiable", "vraiment sérieux",
    "confiance", "j'ai peur d'être trompé", "remboursé si", "garanti",
]

# General financial keyword (catch-all, lower priority)
FINANCIAL_KEYWORDS = [
    "budget", "prix", "investir", "payer",
]

# ── Next challenge request (deferral intent — spec §7.3) ─────────────────────
# Distinct from faq_next_challenge_date (asking when):
# this is a contact who explicitly defers participation to a future edition.
NEXT_CHALLENGE_REQUEST_KEYWORDS = [
    "je reviendrai plus tard",
    "je le ferai la prochaine fois",
    "prochaine fois",
    "je ne peux pas cette fois",
    "pas disponible cette fois",
    "je veux revenir",
    "je reviendrai",
    "pas disponible maintenant",
    "s'inscrire pour la prochaine",
]

# ── Human escalation triggers ─────────────────────────────────────────────────
# These require immediate human handoff regardless of other signals.
ESCALATION_KEYWORDS = [
    "appel", "appel individuel", "remboursement", "avocat", "plainte",
    "conseiller", "parler à quelqu'un", "contact direct",
    "je veux parler", "je veux être rappelé",
]
