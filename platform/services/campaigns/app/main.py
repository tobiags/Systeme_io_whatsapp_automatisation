from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.db.models import (
    CampaignEnrollment,
    ChallengeEdition,
    Consent,
    Contact,
    Message,
    ScoreEvent,
)
from shared.db.session import get_db
from services.campaigns.app.challenge_calendar import get_cohort_config
from services.campaigns.app.rules import DEFAULT_JOURNEY
from services.messaging.app.providers.mock import MockProvider
from services.messaging.app.providers.wati import WatiProvider

router = APIRouter(prefix="/campaigns")


# ── Provider factory ──────────────────────────────────────────────────────────

def _get_provider():
    """Return WatiProvider when credentials are configured, else MockProvider."""
    if settings.wati_api_url and settings.wati_api_token:
        return WatiProvider(settings.wati_api_url, settings.wati_api_token)
    return MockProvider()


# ── Variable builder ──────────────────────────────────────────────────────────

def _build_variables(
    first_name: str,
    template_key: str,
    edition: "ChallengeEdition | None",
    cohort: str,
) -> dict[str, str]:
    """Build Wati template parameter dict for a given contact + template.

    Variable mapping (matches WhatsApp template definitions):
      {{1}} — prénom du contact
      {{2}} — URL StreamYard (day templates only)
      {{3}} — heure de la session (day templates only, e.g. "21:00")
    """
    name = (first_name or "").strip() or "vous"
    variables: dict[str, str] = {"1": name}

    # Day templates need StreamYard URL ({{2}}) and session time ({{3}})
    if "challenge_day_" in template_key:
        cohort_cfg = get_cohort_config(cohort)
        variables["2"] = (edition.streamyard_url or "") if edition else ""
        variables["3"] = cohort_cfg.get("live_time", "21:00")

    return variables


# ── Request models ─────────────────────────────────────────────────────────────

class EnrollRequest(BaseModel):
    contact_id: str
    campaign_key: str
    region: str
    edition_key: str | None = None   # e.g. "2026-05-07-eu"
    current_step: str | None = None  # override starting step (mid-challenge enrollments / tests)


class BroadcastRequest(BaseModel):
    campaign_key: str
    cohort: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
    Send a message to every contact enrolled in campaign_key / cohort at their current journey step.

    For each enrollment:
      1. Checks opt-in consent (spec §4.3) — skips without it.
      2. Applies behavioral branching (main vs catchup template).
      3. Looks up Contact for first_name + phone.
      4. Looks up ChallengeEdition for StreamYard URL (day templates).
      5. Builds template variables: {{1}} first_name, {{2}} URL, {{3}} heure.
      6. Calls WatiProvider (or MockProvider in dev/test).
      7. Persists a Message audit record with real status.
      8. Advances enrollment to the next journey step.
    """
    enrollments = (
        db.query(CampaignEnrollment)
        .filter(
            CampaignEnrollment.campaign_key == payload.campaign_key,
            CampaignEnrollment.cohort == payload.cohort,
        )
        .all()
    )

    provider = _get_provider()
    queued: list[dict] = []
    skipped_no_consent = 0

    for enr in enrollments:
        step_idx = next(
            (i for i, s in enumerate(DEFAULT_JOURNEY) if s.step_key == enr.current_step),
            None,
        )
        if step_idx is None:
            continue  # unknown / completed step — skip

        step = DEFAULT_JOURNEY[step_idx]

        # ── Consent gate (spec §4.3) ──────────────────────────────────────────
        consent = (
            db.query(Consent)
            .filter(Consent.contact_id == enr.contact_id, Consent.status == "opted_in")
            .first()
        )
        if not consent:
            skipped_no_consent += 1
            continue

        # ── Behavioral branching ──────────────────────────────────────────────
        # DAY_2 / DAY_3 / AFTER_1: check prior-day attendance event.
        # Present → continuity template | Absent → catch-up template.
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

        # ── Contact lookup (first_name + phone) ───────────────────────────────
        contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
        # Graceful fallback: in tests contacts may not be persisted in Contact table.
        # Use contact_id as phone placeholder so MockProvider can handle it.
        phone = contact.phone if contact else enr.contact_id
        first_name = contact.first_name if contact else ""

        # ── Edition lookup (StreamYard URL for day templates) ─────────────────
        edition: ChallengeEdition | None = None
        if enr.edition_key:
            edition = (
                db.query(ChallengeEdition)
                .filter(ChallengeEdition.edition_key == enr.edition_key)
                .first()
            )

        # ── Build template variables ──────────────────────────────────────────
        variables = _build_variables(first_name, template_key, edition, enr.cohort)

        # ── Send via provider ─────────────────────────────────────────────────
        result = provider.send_template(phone, template_key, variables)

        # ── Persist audit record ──────────────────────────────────────────────
        msg_id = f"msg_{uuid4().hex[:8]}"
        db.add(Message(
            id=msg_id,
            contact_id=enr.contact_id,
            template_key=template_key,
            variables=variables,
            status=result.get("status", "queued"),
            provider=result.get("provider", "mock"),
        ))

        # ── Step progression ──────────────────────────────────────────────────
        if step_idx + 1 < len(DEFAULT_JOURNEY):
            enr.current_step = DEFAULT_JOURNEY[step_idx + 1].step_key
        else:
            enr.current_step = "completed"

        queued.append({
            "contact_id": enr.contact_id,
            "template_key": template_key,
            "message_id": msg_id,
            "variables": variables,
            "provider": result.get("provider", "mock"),
            "status": result.get("status", "queued"),
        })

    db.commit()
    return {
        "queued": len(queued),
        "skipped_no_consent": skipped_no_consent,
        "messages": queued,
    }


app = FastAPI()
app.include_router(router)
