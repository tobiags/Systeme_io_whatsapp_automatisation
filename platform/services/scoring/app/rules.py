# Scoring rules for the Challenge Amazon FBA engagement platform.
# Points reflect the behavioral signals that matter for conversion:
# live attendance > question asking > link clicks > message opens > registration.
#
# Rules are versioned — do NOT change values without creating a new version and
# migrating existing ContactScore totals if needed.
#
# VERSION: 2

SCORE_RULES: dict[str, int] = {
    # ── Acquisition ──────────────────────────────────────────────────────────
    "registered": 10,               # inscrit via Systeme.io
    "group_whatsapp_joined": 15,    # a rejoint le groupe WhatsApp du challenge

    # ── Message engagement ────────────────────────────────────────────────────
    "opened_message": 5,            # a ouvert un message WhatsApp
    "clicked_link": 10,             # a cliqué un lien quelconque
    "streamyard_link_clicked": 10,  # a cliqué le lien StreamYard du live
    "replied_message": 10,          # a répondu à un message WhatsApp
    "poll_answered": 10,            # a répondu à un sondage / micro-question

    # ── StreamYard registration (registered on the event page) ───────────────
    "day1_streamyard_registered": 5,  # inscrit sur StreamYard J1
    "day2_streamyard_registered": 5,  # inscrit sur StreamYard J2
    "day3_streamyard_registered": 5,  # inscrit sur StreamYard J3

    # ── Live attendance (highest weight — confirms real engagement) ───────────
    "day1_live_joined": 30,         # présent au live Jour 1 (jeudi)
    "day2_live_joined": 25,         # présent au live Jour 2 (vendredi)
    "day3_live_joined": 25,         # présent au live Jour 3 (samedi)
    "confirmed_live": 30,           # alias générique (rétrocompatibilité)

    # ── Absence tracking (0 pts — for audit/segmentation only, spec §5.3) ────
    "day1_live_missed": 0,          # absent au live Jour 1
    "day2_live_missed": 0,          # absent au live Jour 2
    "day3_live_missed": 0,          # absent au live Jour 3

    # ── Conversational signals ────────────────────────────────────────────────
    "asked_question": 20,           # a posé une question pendant le challenge
    "offer_interest_detected": 20,  # a montré un intérêt explicite pour l'offre
    "conversion_intent_detected": 35,  # signal fort d'intention d'achat

    # ── Commercial (highest value) ────────────────────────────────────────────
    "paid_offer": 50,               # a acheté l'offre
}

# Segment thresholds (score → segment):
# ≤ 15  → froid
# ≤ 40  → tiède
# ≤ 75  → chaud
# > 75  → très_chaud
