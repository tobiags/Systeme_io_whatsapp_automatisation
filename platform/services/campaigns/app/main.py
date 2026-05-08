from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import CampaignEnrollment, Consent, Message, ScoreEvent
from shared.db.session import get_db
from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.rules import DEFAULT_JOURNEY

router = APIRouter(prefix="/campaigns")


class EnrollRequest(BaseModel):
    contact_id: str
    campaign_key: str
    region: str
    edition_key: str | None = None   # e.g. "2026-05-07-eu"
    current_step: str | None = None  # override starting step (useful for mid-challenge enrollments)


class BroadcastRequest(BaseModel):
    campaign_key: str
    cohort: str


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_contact(payload: EnrollRequest, db: Session = Depends(get_db)):
    # Allow callers to override the starting step (mid-challenge enrollments / tests).
    start_step = (
        next((s for s in DEFAULT_JOURNEY if s.step_key == payload.current_step), DEFAULT_JOURNEY[0])
        if payload.current_step
        else DEFAULT_JOURNEY[0]
    )
    cohort_config = get_cohort_config(payload.region)
    enrollment = CampaignEnrollment(
        id=f"enr_{uuid4().hex[:8]}",
        contact_id=payload.contact_id,
        campaign_key=payload.campaign_key,
        edition_key=payload.edition_key,
        current_step=start_step.step_key,
        cohort=payload.region,
    )
    db.add(enrollment)
    db.commit()
    return {
        "contact_id": payload.contact_id,
        "campaign_key": payload.campaign_key,
        "edition_key": payload.edition_key,
        "cohort": payload.region,
        "live_timezone": cohort_config["live_timezone"],
        "next_step": {"step_key": start_step.step_key, "template_key": start_step.template_key},
    }


@router.post("/broadcast")
def broadcast_campaign(payload: BroadcastRequest, db: Session = Depends(get_db)):
    """
    Queue a message for every contact enrolled in campaign_key / cohort at their current journey step.
    Returns count of messages queued and their IDs.
    """
    enrollments = (
        db.query(CampaignEnrollment)
        .filter(
            CampaignEnrollment.campaign_key == payload.campaign_key,
            CampaignEnrollment.cohort == payload.cohort,
        )
        .all()
    )

    queued = []
    skipped_no_consent = 0

    for enr in enrollments:
        step_idx = next(
            (i for i, s in enumerate(DEFAULT_JOURNEY) if s.step_key == enr.current_step),
            None,
        )
        if step_idx is None:
            continue  # enrollment on an unknown/completed step — skip

        step = DEFAULT_JOURNEY[step_idx]

        # ── Consent gate (spec §4.3) ──────────────────────────────────────────
        # Every campaign message must be gated by consent eligibility.
        consent = (
            db.query(Consent)
            .filter(
                Consent.contact_id == enr.contact_id,
                Consent.status == "opted_in",
            )
            .first()
        )
        if not consent:
            skipped_no_consent += 1
            continue

        # ── Behavioral branching ──────────────────────────────────────────────
        # For DAY_2 and DAY_3, check whether the contact attended the prior day.
        # Present → continuity template (challenge_day_N)
        # Absent  → catch-up template   (challenge_day_N_catchup)
        template_key = step.template_key
        if step.catchup_template_key and step.attendance_event:
            attended = (
                db.query(ScoreEvent)
                .filter(
                    ScoreEvent.contact_id == enr.contact_id,
                    ScoreEvent.event_type == step.attendance_event,
                )
                .first()
            )
            if not attended:
                template_key = step.catchup_template_key

        msg_id = f"msg_{uuid4().hex[:8]}"
        db.add(Message(
            id=msg_id,
            contact_id=enr.contact_id,
            template_key=template_key,
            variables={},
            status="queued",
            provider="mock",
        ))

        # ── Step progression ──────────────────────────────────────────────────
        # Advance the contact to the next journey step after queuing.
        # If already at the last step, mark as completed.
        if step_idx + 1 < len(DEFAULT_JOURNEY):
            enr.current_step = DEFAULT_JOURNEY[step_idx + 1].step_key
        else:
            enr.current_step = "completed"

        queued.append({
            "contact_id": enr.contact_id,
            "template_key": template_key,
            "message_id": msg_id,
        })

    db.commit()
    return {
        "queued": len(queued),
        "skipped_no_consent": skipped_no_consent,
        "messages": queued,
    }


app = FastAPI()
app.include_router(router)
