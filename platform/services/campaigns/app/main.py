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
from services.campaigns.app.rules import DEFAULT_JOURNEY, compute_start_step
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
      {{1}} — prénom du contact (all templates)
      {{2}} — heure de la session (countdown_j1 only — "À ce soir à {{2}} !")
      {{2}} — per-day StreamYard registration URL (live_day{1,2,3}* templates)
      {{2}} — programme payment URL (live_day3_offer / live_day3_offer_hplus2)
      {{2}} — replay day 1 URL (post_replay_* templates)
      {{3}} — replay day 2 URL (post_replay_* templates)
      {{4}} — replay day 3 URL (post_replay_* templates)
      {{2}} — OnceHub form URL (post_closer_call and legacy post_* closer templates)
      {{3}} — heure de la session (live_day* templates)
    """
    name = (first_name or "").strip() or "vous"
    variables: dict[str, str] = {"1": name}

    cohort_cfg = get_cohort_config(cohort)
    live_time = cohort_cfg.get("live_time", "21:00")

    # countdown_j1: only needs the session time ({{2}})
    if template_key == "countdown_j1":
        variables["2"] = live_time

    # H+2 Day 3 offer: programme payment link ({{2}})
    elif template_key in {"live_day3_offer", "live_day3_offer_hplus2"}:
        variables["2"] = (
            (edition.payment_url if edition else None)
            or settings.program_payment_url
            or ""
        )

    # post-challenge replay templates: 3 replay links ({{2}}, {{3}}, {{4}})
    elif template_key in {"post_recap_registered_absent", "post_recap_not_registered"} or template_key.startswith("post_replay_"):
        variables["2"] = (
            (edition.replay_day1_url if edition else None)
            or settings.replay_day1_url
            or ""
        )
        variables["3"] = (
            (edition.replay_day2_url if edition else None)
            or settings.replay_day2_url
            or ""
        )
        variables["4"] = (
            (edition.replay_day3_url if edition else None)
            or settings.replay_day3_url
            or ""
        )

    # post-challenge closer booking templates
    elif template_key in {"post_closer_call", "post_followup", "post_recap_attended"}:
        variables["2"] = (
            (edition.closer_booking_url if edition else None)
            or settings.oncehub_form_url
            or ""
        )

    # live day templates: per-day StreamYard registration URL ({{2}}) + time ({{3}})
    elif template_key.startswith("live_day"):
        # Route to the per-day URL field; fall back to legacy streamyard_url
        if template_key.startswith("live_day1"):
            url = (edition.day1_url or edition.streamyard_url or "") if edition else ""
        elif template_key.startswith("live_day2"):
            url = (edition.day2_url or edition.streamyard_url or "") if edition else ""
        elif template_key.startswith("live_day3"):
            url = (edition.day3_url or edition.streamyard_url or "") if edition else ""
        else:
            url = (edition.streamyard_url or "") if edition else ""
        variables["2"] = url
        variables["3"] = live_time

    return variables


def _has_paid_offer(contact_id: str, db: Session) -> bool:
    return (
        db.query(ScoreEvent)
        .filter(
            ScoreEvent.contact_id == contact_id,
            ScoreEvent.event_type == "paid_offer",
        )
        .first()
        is not None
    )


# ── Request models ─────────────────────────────────────────────────────────────

class EnrollRequest(BaseModel):
    contact_id: str
    campaign_key: str
    region: str
    edition_key: str | None = None        # e.g. "2026-05-07-eu"
    current_step: str | None = None       # explicit override (tests / mid-challenge)
    days_until_challenge: int | None = None  # smart-skip: days before challenge starts


class BroadcastRequest(BaseModel):
    campaign_key: str
    cohort: str


class Day3OfferRequest(BaseModel):
    campaign_key: str
    cohort: str
    edition_key: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_contact(payload: EnrollRequest, db: Session = Depends(get_db)):
    """Enroll a contact into a campaign journey.

    Starting step priority:
      1. `current_step` explicit override (tests, manual mid-challenge enrollments).
      2. `days_until_challenge` smart-skip: late registrants jump to the right
         countdown step (e.g. J-3 registrant skips J-7/J-6/J-5/J-4 steps).
      3. Default: first step of DEFAULT_JOURNEY (WELCOME).
    """
    if payload.current_step:
        start_step = next(
            (s for s in DEFAULT_JOURNEY if s.step_key == payload.current_step),
            DEFAULT_JOURNEY[0],
        )
    elif payload.days_until_challenge is not None:
        skip_to_key = compute_start_step(payload.days_until_challenge)
        start_step = next(
            (s for s in DEFAULT_JOURNEY if s.step_key == skip_to_key),
            DEFAULT_JOURNEY[0],
        )
    else:
        start_step = DEFAULT_JOURNEY[0]

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
      2. Applies 3-way behavioral branching for DAY_2 / DAY_3 / AFTER_1:
           a. day{N}_live_joined event exists         → main (attended) template
           b. day{N}_streamyard_registered only       → registered_absent template
           c. neither event                           → no_show template
      3. Looks up Contact for first_name + phone.
      4. Looks up ChallengeEdition for StreamYard URL (live day templates).
      5. Builds template variables: {{1}} first_name, {{2}} URL or time, {{3}} time.
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
    skipped_paid_offer = 0

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

        if _has_paid_offer(enr.contact_id, db):
            skipped_paid_offer += 1
            enr.current_step = "completed"
            continue

        # ── 3-way behavioral branching ────────────────────────────────────────
        # Only applies to steps that have branching templates configured.
        template_key = step.template_key
        if step.attendance_event:
            attended = (
                db.query(ScoreEvent)
                .filter(
                    ScoreEvent.contact_id == enr.contact_id,
                    ScoreEvent.event_type == step.attendance_event,
                )
                .first()
            )
            if attended:
                # Branch (a): attended the live → main template (already set)
                pass
            elif step.registration_event:
                registered = (
                    db.query(ScoreEvent)
                    .filter(
                        ScoreEvent.contact_id == enr.contact_id,
                        ScoreEvent.event_type == step.registration_event,
                    )
                    .first()
                )
                if registered and step.registered_absent_template_key:
                    # Branch (b): registered on StreamYard but didn't attend
                    template_key = step.registered_absent_template_key
                elif step.no_show_template_key:
                    # Branch (c): never registered on StreamYard
                    template_key = step.no_show_template_key
            elif step.no_show_template_key:
                # No registration_event configured → fall back to no_show
                template_key = step.no_show_template_key

        # ── Contact lookup (first_name + phone) ───────────────────────────────
        contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
        phone = contact.phone if contact else enr.contact_id
        first_name = contact.first_name if contact else ""

        # ── Edition lookup (StreamYard URL for live day templates) ────────────
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
            provider_message_id=result.get("provider_message_id"),
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
        "skipped_paid_offer": skipped_paid_offer,
        "messages": queued,
    }


@router.post("/trigger/day3-offer")
def trigger_day3_offer(payload: Day3OfferRequest, db: Session = Depends(get_db)):
    """Manually send the H+2 Day-3 payment link to Day-3 registered prospects.

    Filters enrolled contacts to those who have a `day3_streamyard_registered`
    ScoreEvent — i.e. they signed up for Day 3 via StreamYard (best available
    proxy for "watching right now").

    The operator triggers this endpoint ~2 hours into the Day-3 live session,
    when the programme offer is shared on screen.
    """
    query = db.query(CampaignEnrollment).filter(
        CampaignEnrollment.campaign_key == payload.campaign_key,
        CampaignEnrollment.cohort == payload.cohort,
    )
    if payload.edition_key:
        query = query.filter(CampaignEnrollment.edition_key == payload.edition_key)
    enrollments = query.all()

    edition: ChallengeEdition | None = None
    if payload.edition_key:
        edition = (
            db.query(ChallengeEdition)
            .filter(ChallengeEdition.edition_key == payload.edition_key)
            .first()
        )

    provider = _get_provider()
    template_key = "live_day3_offer_hplus2"
    sent = 0
    skipped_no_consent = 0
    skipped_not_registered = 0
    skipped_paid_offer = 0

    for enr in enrollments:
        # Consent gate
        consent = (
            db.query(Consent)
            .filter(Consent.contact_id == enr.contact_id, Consent.status == "opted_in")
            .first()
        )
        if not consent:
            skipped_no_consent += 1
            continue

        if _has_paid_offer(enr.contact_id, db):
            skipped_paid_offer += 1
            continue

        # Only send to contacts who registered for Day 3 on StreamYard
        registered = (
            db.query(ScoreEvent)
            .filter(
                ScoreEvent.contact_id == enr.contact_id,
                ScoreEvent.event_type == "day3_streamyard_registered",
            )
            .first()
        )
        if not registered:
            skipped_not_registered += 1
            continue

        contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
        phone = contact.phone if contact else enr.contact_id
        first_name = contact.first_name if contact else ""

        variables = _build_variables(first_name, template_key, edition, enr.cohort)
        result = provider.send_template(phone, template_key, variables)

        db.add(Message(
            id=f"msg_{uuid4().hex[:8]}",
            contact_id=enr.contact_id,
            template_key=template_key,
            variables=variables,
            provider_message_id=result.get("provider_message_id"),
            status=result.get("status", "queued"),
            provider=result.get("provider", "mock"),
        ))
        sent += 1

    db.commit()
    return {
        "sent": sent,
        "skipped_no_consent": skipped_no_consent,
        "skipped_not_registered": skipped_not_registered,
        "skipped_paid_offer": skipped_paid_offer,
        "template_key": template_key,
    }


app = FastAPI()
app.include_router(router)
