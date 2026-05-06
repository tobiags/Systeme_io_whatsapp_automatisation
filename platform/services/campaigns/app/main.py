from fastapi import FastAPI, status
from pydantic import BaseModel

from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.rules import DEFAULT_JOURNEY

app = FastAPI()


class EnrollRequest(BaseModel):
    contact_id: str
    campaign_key: str
    region: str


@app.post("/campaigns/enroll", status_code=status.HTTP_201_CREATED)
def enroll_contact(payload: EnrollRequest):
    next_step = DEFAULT_JOURNEY[0]
    cohort_config = get_cohort_config(payload.region)
    return {
        "contact_id": payload.contact_id,
        "campaign_key": payload.campaign_key,
        "cohort": payload.region,
        "live_timezone": cohort_config["live_timezone"],
        "next_step": {"step_key": next_step.step_key, "template_key": next_step.template_key},
    }
