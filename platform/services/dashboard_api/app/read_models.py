from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.db.models import (
    CampaignEnrollment,
    Contact,
    InboundMessage,
    ScoreEvent,
    Segment,
)


def get_dashboard_summary(db: Session) -> dict:
    contacts_total = db.query(Contact).count()

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

    # Conversion rate = contacts with at least one "paid_offer" event / total contacts
    paid_count = (
        db.query(func.count(func.distinct(ScoreEvent.contact_id)))
        .filter(ScoreEvent.event_type == "paid_offer")
        .scalar()
        or 0
    )
    conversion_rate = round(paid_count / contacts_total, 4) if contacts_total > 0 else 0.0

    # Segment distribution (latest segment per contact)
    segment_counts = {"froid": 0, "tiede": 0, "chaud": 0, "tres_chaud": 0}
    for seg, count in (
        db.query(Segment.segment, func.count(Segment.id))
        .group_by(Segment.segment)
        .all()
    ):
        if seg in segment_counts:
            segment_counts[seg] = count

    # Cohort distribution
    cohort_counts = {"EU": 0, "US-CA": 0}
    for cohort, count in (
        db.query(CampaignEnrollment.cohort, func.count(CampaignEnrollment.id))
        .group_by(CampaignEnrollment.cohort)
        .all()
    ):
        cohort_counts[cohort] = count

    return {
        "contacts_total": contacts_total,
        "campaigns_active": campaigns_active,
        "manual_followups": manual_followups,
        "conversion_rate": conversion_rate,
        "contacts_by_segment": segment_counts,
        "contacts_by_cohort": cohort_counts,
    }
