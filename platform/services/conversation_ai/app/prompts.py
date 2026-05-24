# â”€â”€ FAQ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each entry: keyword (lowercased) â†’ (answer, intent_id)
# Intent IDs match the spec: faq_whatsapp_group_join, faq_email_missing, etc.

FAQ: dict[str, tuple[str, str]] = {
    # Quand Ã§a commence
    "quand ca commence": (
        "Le Challenge Amazon FBA se dÃ©roule du jeudi au samedi selon votre zone horaire. "
        "Vous recevrez le lien de connexion avant chaque session.",
        "faq_start_time",
    ),
    "quand est-ce que cela commence": (
        "Le Challenge Amazon FBA se dÃ©roule du jeudi au samedi selon votre zone horaire. "
        "Vous recevrez le lien de connexion avant chaque session.",
        "faq_start_time",
    ),
    "quand est ce que ca commence": (
        "Le Challenge Amazon FBA se dÃƒÂ©roule du jeudi au samedi selon votre zone horaire. "
        "Vous recevrez le lien de connexion avant chaque session.",
        "faq_start_time",
    ),
    "quand commence": (
        "Le Challenge Amazon FBA se dÃ©roule du jeudi au samedi selon votre zone horaire.",
        "faq_start_time",
    ),
    "c'est quoi le challenge": (
        "Le Challenge Amazon FBA est un accompagnement gratuit en 3 sessions live pour comprendre comment lancer un business Amazon FBA pas Ã  pas.",
        "faq_challenge_overview",
    ),
    "c est quoi le challenge": (
        "Le Challenge Amazon FBA est un accompagnement gratuit en 3 sessions live pour comprendre comment lancer un business Amazon FBA pas Ã  pas.",
        "faq_challenge_overview",
    ),
    "comment Ã§a marche": (
        "Le challenge se dÃ©roule sur 3 sessions live gratuites. Vous recevez les liens sur WhatsApp avant chaque session, puis on avance Ã©tape par Ã©tape pendant le parcours.",
        "faq_challenge_overview",
    ),
    "comment ca marche": (
        "Le challenge se dÃ©roule sur 3 sessions live gratuites. Vous recevez les liens sur WhatsApp avant chaque session, puis on avance Ã©tape par Ã©tape pendant le parcours.",
        "faq_challenge_overview",
    ),

    # Groupe WhatsApp
    "comment rejoindre le groupe whatsapp": (
        "Le lien du groupe WhatsApp vous est envoyÃ© dans la sÃ©quence de bienvenue aprÃ¨s votre inscription. "
        "VÃ©rifiez vos messages WhatsApp ou vos emails.",
        "faq_whatsapp_group_join",
    ),
    "rejoindre le groupe": (
        "Le lien du groupe WhatsApp vous a Ã©tÃ© envoyÃ© par message aprÃ¨s votre inscription.",
        "faq_whatsapp_group_join",
    ),
    "lien du groupe": (
        "Le lien du groupe WhatsApp vous a Ã©tÃ© envoyÃ© par message aprÃ¨s votre inscription.",
        "faq_whatsapp_group_join",
    ),

    # Email manquant
    "je me suis inscrit mais je n'ai pas recu d'email": (
        "VÃ©rifiez vos spams et courriers indÃ©sirables. "
        "Si vous ne trouvez toujours pas, rÃ©pondez ici avec votre adresse email et nous vÃ©rifierons.",
        "faq_email_missing",
    ),
    "pas recu d'email": (
        "VÃ©rifiez vos spams. Si le problÃ¨me persiste, rÃ©pondez ici avec votre adresse email.",
        "faq_email_missing",
    ),
    "pas recu le lien": (
        "Le lien de live est envoyÃ© par email et WhatsApp avant chaque session. "
        "VÃ©rifiez vos spams ou rÃ©pondez ici pour que nous vÃ©rifiions.",
        "faq_email_missing",
    ),

    # Prix de la formation
    "combien coute la formation": (
        "Le Challenge Amazon FBA est entiÃ¨rement gratuit. "
        "Les dÃ©tails de la formation complÃ¨te sont prÃ©sentÃ©s pendant et Ã  la fin du challenge.",
        "faq_offer_price",
    ),
    "combien ca coute": (
        "Le challenge est gratuit. Les dÃ©tails de l'offre de formation sont prÃ©sentÃ©s pendant le parcours.",
        "faq_offer_price",
    ),
    "c'est gratuit": (
        "Oui, le Challenge Amazon FBA est 100% gratuit. "
        "Une offre de formation est prÃ©sentÃ©e Ã  la fin pour ceux qui souhaitent aller plus loin.",
        "faq_offer_price",
    ),

    # Prochain challenge
    "quand est-ce que vous referez un nouveau challenge": (
        "Le Challenge Amazon FBA a lieu 2 fois par mois, du jeudi au samedi. "
        "Restez abonnÃ© Ã  nos messages pour Ãªtre informÃ© des prochaines dates.",
        "faq_next_challenge_date",
    ),
    "prochain challenge": (
        "Le prochain Challenge Amazon FBA aura lieu prochainement. "
        "Vous serez notifiÃ© par WhatsApp dÃ¨s que les inscriptions sont ouvertes.",
        "faq_next_challenge_date",
    ),
    "prochaine edition": (
        "Le Challenge Amazon FBA a lieu 2 fois par mois. "
        "Vous recevrez un message dÃ¨s que la prochaine Ã©dition est disponible.",
        "faq_next_challenge_date",
    ),
}

# â€”â€” Qualification / niveau de dÃ©part â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
# Used right after welcome when a lead answers with their starting level.
BEGINNER_PROFILE_KEYWORDS = [
    "je pars de zero",
    "je pars de zÃ©ro",
    "je commence de zero",
    "je commence de zÃ©ro",
    "je repars de zero",
    "je repars de zÃ©ro",
    "je part de zero",
    "je part de zÃ©ro",
    "alors oui je pars de zÃ©ro",
    "bonjour je pars de zero",
    "bonjour je pars de zÃ©ro",
    "je suis debutant",
    "je suis dÃ©butant",
    "debutant",
    "dÃ©butant",
    "je n'ai pas encore commence",
    "je n'ai pas encore commencÃ©",
    "je ne pas encore je vais partir Ã  zÃ©ro",
    "je vais partir de zero",
    "je vais partir de zÃ©ro",
    "de 0",
    "a zero",
    "Ã  zÃ©ro",
    "zero",
    "zÃ©ro",
    "je voudrais commencer",
    "je veux commencer",
    "je veux debuter",
    "je veux dÃ©buter",
]

STARTED_PROFILE_KEYWORDS = [
    "j'ai deja commence",
    "j'ai dÃ©jÃ  commencÃ©",
    "j'ai deja vendu",
    "j'ai dÃ©jÃ  vendu",
    "j'ai commence",
    "j'ai commencÃ©",
    "je vends deja",
    "je vends dÃ©jÃ ",
    "je vends en ligne",
    "j'ai un peu d'experience",
    "j'ai un peu d'expÃ©rience",
    "j'ai de l'experience",
    "j'ai de l'expÃ©rience",
    "je connais deja amazon fba",
    "je connais dÃ©jÃ  amazon fba",
]

TIME_OBJECTION_KEYWORDS = [
    "pas le temps",
    "je manque de temps",
    "le temps",
    "je n'ai pas le temps",
    "je n ai pas le temps",
    "trop occupe",
    "trop occupÃ©",
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

# â”€â”€ Financial objection classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each group maps to a specific intent and reply strategy.

# Soft: general budget concern without specific action signal
FINANCIAL_SOFT_KEYWORDS = [
    "trop cher", "c'est cher", "pas le budget", "pas les moyens",
    "je n'ai pas le budget", "manque d'argent", "coÃ»t", "coute",
    "je veux rÃ©flÃ©chir", "pas sÃ»r de pouvoir investir",
]

# Strong: explicit refusal or repeated objection with no engagement
FINANCIAL_STRONG_KEYWORDS = [
    "impossible pour moi", "hors de prix", "jamais Ã  ce prix",
    "trop risquÃ©", "je ne peux vraiment pas",
]

# Installment / payment plan request
INSTALLMENT_KEYWORDS = [
    "payer en plusieurs fois", "payer en 2 fois", "payer en 3 fois",
    "payer en 10 fois", "plan de paiement", "facilitÃ©s de paiement",
    "mensualitÃ©s", "Ã©chelonner",
]

# Payment attempt failure
PAYMENT_FAILURE_KEYWORDS = [
    "essayÃ© de payer", "essayÃ© de payer mais", "paiement refusÃ©",
    "fonds insuffisants", "pas assez sur mon compte", "carte refusÃ©e",
    "paiement Ã©chouÃ©", "j'ai pas pu payer",
]

# Sceptic / trust objection
SCEPTIC_KEYWORDS = [
    "j'ai peur de perdre", "arnaque", "fiable", "vraiment sÃ©rieux",
    "confiance", "j'ai peur d'Ãªtre trompÃ©", "remboursÃ© si", "garanti",
]

# General financial keyword (catch-all, lower priority)
FINANCIAL_KEYWORDS = [
    "budget", "prix", "investir", "payer",
]

# â”€â”€ Next challenge request (deferral intent â€” spec Â§7.3) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

# â”€â”€ Human escalation triggers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These require immediate human handoff regardless of other signals.
ESCALATION_KEYWORDS = [
    "appel", "appel individuel", "remboursement", "avocat", "plainte",
    "conseiller", "parler Ã  quelqu'un", "contact direct",
    "je veux parler", "je veux Ãªtre rappelÃ©",
]
