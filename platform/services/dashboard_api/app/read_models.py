from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.db.models import (
    CampaignEnrollment,
    ChallengeEdition,
    Contact,
    InboundMessage,
    Message,
    ScoreEvent,
    Segment,
)

# Intent IDs that count as financial objections
_FINANCIAL_INTENTS = {
    "objection_financial_soft",
    "objection_financial_strong",
    "financial_objection",
    "installment_plan_request",
    "payment_failure_followup_needed",
    "skeptic_trust_objection",
}

# Intent IDs that count as FAQ hits
_FAQ_INTENTS = {
    "faq_start_time",
    "faq_whatsapp_group_join",
    "faq_email_missing",
    "faq_offer_price",
    "faq_next_challenge_date",
}


def _parse_edition_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _select_active_edition(editions: list[ChallengeEdition]) -> ChallengeEdition | None:
    """Choose a meaningful active edition for the dashboard.

    Prefer the nearest upcoming valid edition. If there is no future edition,
    show the latest valid past edition. Invalid operator-created rows are ignored
    so the dashboard does not present them as the active campaign.
    """
    today = date.today()
    valid = [(edition, parsed) for edition in editions if (parsed := _parse_edition_date(edition.edition_date))]
    if not valid:
        return None

    future = [(edition, parsed) for edition, parsed in valid if parsed >= today]
    if future:
        return min(future, key=lambda item: item[1])[0]
    return max(valid, key=lambda item: item[1])[0]


def get_dashboard_summary(db: Session) -> dict:
    contacts_total = db.query(Contact).count()
    enrollments_total = db.query(CampaignEnrollment).count()
    enrolled_contacts_total = (
        db.query(func.count(func.distinct(CampaignEnrollment.contact_id))).scalar()
        or 0
    )
    contacts_without_enrollment = max(contacts_total - enrolled_contacts_total, 0)

    # Total messages sent (all statuses — queued + sent + failed)
    messages_sent_total = db.query(Message).count()

    campaigns_active = (
        db.query(func.count(func.distinct(CampaignEnrollment.campaign_key))).scalar() or 0
    )

    # Contacts whose last inbound message still needs human review
    manual_followups = (
        db.query(func.count(func.distinct(InboundMessage.contact_id)))
        .filter(InboundMessage.needs_human.is_(True))
        .scalar()
        or 0
    )

    # Conversion rate = contacts with at least one "paid_offer" event / total
    paid_count = (
        db.query(func.count(func.distinct(ScoreEvent.contact_id)))
        .filter(ScoreEvent.event_type == "paid_offer")
        .scalar()
        or 0
    )
    conversion_rate = round(paid_count / contacts_total, 4) if contacts_total > 0 else 0.0

    # ── Segment distribution ──────────────────────────────────────────────────
    segment_counts = {"froid": 0, "tiede": 0, "chaud": 0, "tres_chaud": 0}
    for seg, count in (
        db.query(Segment.segment, func.count(Segment.id))
        .group_by(Segment.segment)
        .all()
    ):
        if seg in segment_counts:
            segment_counts[seg] = count

    # ── Cohort distribution ───────────────────────────────────────────────────
    cohort_counts: dict[str, int] = {}
    for cohort, count in (
        db.query(CampaignEnrollment.cohort, func.count(CampaignEnrollment.id))
        .group_by(CampaignEnrollment.cohort)
        .all()
    ):
        cohort_counts[cohort] = count

    # ── Live attendance per day ───────────────────────────────────────────────
    live_attendance: dict[str, int] = {"day1": 0, "day2": 0, "day3": 0}
    for event_type, count in (
        db.query(ScoreEvent.event_type, func.count(func.distinct(ScoreEvent.contact_id)))
        .filter(ScoreEvent.event_type.in_(["day1_live_joined", "day2_live_joined", "day3_live_joined"]))
        .group_by(ScoreEvent.event_type)
        .all()
    ):
        key = event_type.replace("_live_joined", "")  # day1_live_joined → day1
        live_attendance[key] = count

    # ── Dominant FAQs from inbound messages ──────────────────────────────────
    faq_counts: dict[str, int] = {}
    for intent, count in (
        db.query(InboundMessage.intent, func.count(InboundMessage.id))
        .filter(InboundMessage.intent.in_(list(_FAQ_INTENTS)))
        .group_by(InboundMessage.intent)
        .all()
    ):
        faq_counts[intent] = count

    # ── Financial objections detected ────────────────────────────────────────
    financial_objections_total = (
        db.query(func.count(InboundMessage.id))
        .filter(InboundMessage.intent.in_(list(_FINANCIAL_INTENTS)))
        .scalar()
        or 0
    )
    financial_objections_by_type: dict[str, int] = {}
    for intent, count in (
        db.query(InboundMessage.intent, func.count(InboundMessage.id))
        .filter(InboundMessage.intent.in_(list(_FINANCIAL_INTENTS)))
        .group_by(InboundMessage.intent)
        .all()
    ):
        financial_objections_by_type[intent] = count

    # ── Active edition ────────────────────────────────────────────────────────
    latest_edition = _select_active_edition(db.query(ChallengeEdition).all())
    active_edition = (
        {
            "edition_key": latest_edition.edition_key,
            "cohort": latest_edition.cohort,
            "edition_date": latest_edition.edition_date,
            "streamyard_url": latest_edition.streamyard_url,
        }
        if latest_edition
        else None
    )

    return {
        # Core KPIs
        "contacts_total": contacts_total,
        "enrollments_total": enrollments_total,
        "contacts_without_enrollment": contacts_without_enrollment,
        "messages_sent_total": messages_sent_total,
        "campaigns_active": campaigns_active,
        "manual_followups": manual_followups,
        "conversion_rate": conversion_rate,
        # Breakdown
        "contacts_by_segment": segment_counts,
        "contacts_by_cohort": cohort_counts,
        # Challenge-specific
        "active_edition": active_edition,
        "live_attendance_by_day": live_attendance,
        "faq_counts": faq_counts,
        "financial_objections_total": financial_objections_total,
        "financial_objections_by_type": financial_objections_by_type,
    }
