from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.db.models import CampaignEnrollment, Contact, Segment


def get_dashboard_summary(db: Session) -> dict:
    contacts_total = db.query(Contact).count()
    campaigns_active = (
        db.query(func.count(func.distinct(CampaignEnrollment.campaign_key))).scalar() or 0
    )

    segment_counts = {"froid": 0, "tiede": 0, "chaud": 0, "tres_chaud": 0}
    for seg, count in db.query(Segment.segment, func.count(Segment.id)).group_by(Segment.segment).all():
        if seg in segment_counts:
            segment_counts[seg] = count

    cohort_counts = {"EU": 0, "US-CA": 0}
    for cohort, count in (
        db.query(CampaignEnrollment.cohort, func.count(CampaignEnrollment.id))
        .group_by(CampaignEnrollment.cohort)
        .all()
    ):
        if cohort in cohort_counts:
            cohort_counts[cohort] = count

    return {
        "contacts_total": contacts_total,
        "campaigns_active": campaigns_active,
        "manual_followups": 0,
        "conversion_rate": 0.0,
        "contacts_by_segment": segment_counts,
        "contacts_by_cohort": cohort_counts,
    }
