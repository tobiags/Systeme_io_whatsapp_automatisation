from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import CampaignEnrollment, Message
from shared.db.session import get_db
from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.rules import DEFAULT_JOURNEY

router = APIRouter(prefix="/campaigns")


class EnrollRequest(BaseModel):
    contact_id: str
    campaign_key: str
    region: str


class BroadcastRequest(BaseModel):
    campaign_key: str
    cohort: str


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_contact(payload: EnrollRequest, db: Session = Depends(get_db)):
    next_step = DEFAULT_JOURNEY[0]
    cohort_config = get_cohort_config(payload.region)
    enrollment = CampaignEnrollment(
        id=f"enr_{uuid4().hex[:8]}",
        contact_id=payload.contact_id,
        campaign_key=payload.campaign_key,
        current_step=next_step.step_key,
        cohort=payload.region,
    )
    db.add(enrollment)
    db.commit()
    return {
        "contact_id": payload.contact_id,
        "campaign_key": payload.campaign_key,
        "cohort": payload.region,
        "live_timezone": cohort_config["live_timezone"],
        "next_step": {"step_key": next_step.step_key, "template_key": next_step.template_key},
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
    for enr in enrollments:
        step = next((s for s in DEFAULT_JOURNEY if s.step_key == enr.current_step), None)
        if not step:
            continue  # enrollment on an unknown step — skip

        msg_id = f"msg_{uuid4().hex[:8]}"
        db.add(Message(
            id=msg_id,
            contact_id=enr.contact_id,
            template_key=step.template_key,
            variables={},
            status="queued",
            provider="mock",
        ))
        queued.append({
            "contact_id": enr.contact_id,
            "template_key": step.template_key,
            "message_id": msg_id,
        })

    db.commit()
    return {"queued": len(queued), "messages": queued}


app = FastAPI()
app.include_router(router)
