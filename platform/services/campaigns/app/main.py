from datetime import date, datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.db.models import (
    AuditEvent,
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
from services.campaigns.app.utils import broadcast_already_recorded, broadcast_audit_id, resolve_template_key
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

    # Normalise: strip _utility suffix so pattern matching works identically
    # for both MARKETING and UTILITY variants of the same template.
    base_key = template_key.removesuffix("_utility")

    # countdown_j1: only needs the session time ({{2}})
    if base_key == "countdown_j1":
        variables["2"] = live_time

    # H+2 Day 3 offer: programme payment link ({{2}})
    elif base_key in {"live_day3_offer", "live_day3_offer_hplus2"}:
        variables["2"] = (
            (edition.payment_url if edition else None)
            or settings.program_payment_url
            or ""
        )

    # post_recap for non-attendees/no-shows: 3 replay links {{2}}{{3}}{{4}}
    # Template body: "Jour 1 : {{2}}\nJour 2 : {{3}}\nJour 3 : {{4}}"
    elif base_key in {"post_recap_registered_absent", "post_recap_not_registered"}:
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

    # post-challenge closer / booking templates: {{2}} = closer booking URL
    # (post_recap_attended, post_closer_call, post_followup)
    elif base_key in {
        "post_closer_call",
        "post_followup",
        "post_recap_attended",
    }:
        variables["2"] = (
            (edition.closer_booking_url if edition else None)
            or settings.oncehub_form_url
            or ""
        )

    # post_testimonials / post_inaction_reason: only {{1}} = first_name (no URL)
    elif base_key in {"post_testimonials", "post_inaction_reason"}:
        pass  # variables already contains {"1": name}

    # live day templates: per-day StreamYard URL ({{2}}) + live time ({{3}})
    elif base_key.startswith("live_day"):
        if base_key.startswith("live_day1"):
            url = (edition.day1_url or edition.streamyard_url or "") if edition else ""
        elif base_key.startswith("live_day2"):
            url = (edition.day2_url or edition.streamyard_url or "") if edition else ""
        elif base_key.startswith("live_day3"):
            url = (edition.day3_url or edition.streamyard_url or "") if edition else ""
        else:
            url = (edition.streamyard_url or "") if edition else ""
        variables["2"] = url
        variables["3"] = live_time

    return variables


# _is_us_ca_phone and resolve_template_key are imported from utils.py.
# Do not define them here — keep a single source of truth.


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

def _local_broadcast_date(cohort: str, now_utc: datetime | None = None) -> date:
    cohort_config = get_cohort_config(cohort)
    tz = ZoneInfo(cohort_config["timezone"])
    current_utc = now_utc or datetime.now(timezone.utc)
    return current_utc.astimezone(tz).date()


# _broadcast_audit_id and _broadcast_already_recorded are imported from utils.py
# (single source of truth — tasks.py uses the same functions).
# Local aliases kept for backward-compat with callers inside this file.
_broadcast_audit_id = broadcast_audit_id
_broadcast_already_recorded = broadcast_already_recorded


def _record_manual_broadcast_audit(
    db: Session,
    edition: ChallengeEdition,
    local_day: date,
    payload: dict,
) -> None:
    db.add(AuditEvent(
        name="campaign_daily_broadcast",
        aggregate_id=broadcast_audit_id(edition.edition_key, local_day),
        payload={
            "source": "manual_api",
            "campaign_key": edition.campaign_key,
            "cohort": edition.cohort,
            "edition_key": edition.edition_key,
            "local_date": local_day.isoformat(),
            **payload,
        },
    ))
    db.commit()


_SCHEDULED_STEP_OFFSETS = {
    "COUNTDOWN_J6": -6,
    "COUNTDOWN_J5": -5,
    "COUNTDOWN_J4": -4,
    "COUNTDOWN_J3": -3,
    "COUNTDOWN_J2": -2,
    "COUNTDOWN_J1": -1,
    "DAY_1": 0,
    "DAY_2": 1,
    "DAY_3": 2,
    "AFTER_1": 3,
    "AFTER_2": 4,
    "AFTER_3": 5,
    "AFTER_4": 6,
}


def _step_is_due_on_local_date(step_key: str, edition_date: str | None, local_day: date | None) -> bool:
    if not local_day or not edition_date:
        return True
    offset = _SCHEDULED_STEP_OFFSETS.get(step_key)
    if offset is None:
        return True
    try:
        edition_day = date.fromisoformat(edition_date)
    except ValueError:
        return True
    return (local_day - edition_day).days == offset


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
    edition_key: str | None = None


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


def broadcast_campaign_impl(
    db: Session,
    *,
    campaign_key: str,
    cohort: str,
    edition_key: str | None = None,
    scheduled_local_date: date | None = None,
):
    """Send the current journey step for every enrollment in a cohort or edition."""
    query = (
        db.query(CampaignEnrollment)
        .filter(
            CampaignEnrollment.campaign_key == campaign_key,
            CampaignEnrollment.cohort == cohort,
        )
    )
    if edition_key:
        query = query.filter(CampaignEnrollment.edition_key == edition_key)
    enrollments = query.all()

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

        edition: ChallengeEdition | None = None
        if enr.edition_key:
            edition = (
                db.query(ChallengeEdition)
                .filter(ChallengeEdition.edition_key == enr.edition_key)
                .first()
            )
        if not _step_is_due_on_local_date(
            enr.current_step,
            edition.edition_date if edition else None,
            scheduled_local_date,
        ):
            continue

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

        # edition is already resolved above for _step_is_due_on_local_date.
        # Do NOT re-query here — the second assignment would shadow the first
        # and reset edition to None for any enrollment without edition_key,
        # causing empty {{2}} / {{3}} variables in all live-day templates.

        # ── US/CA UTILITY routing ─────────────────────────────────────────────
        # Meta blocks MARKETING templates for +1 numbers.
        # resolve_template_key routes to _utility ONLY when the variant exists.
        template_key = resolve_template_key(template_key, phone)

        # ── Build template variables ──────────────────────────────────────────
        variables = _build_variables(first_name, template_key, edition, enr.cohort)

        # ── Send via provider ─────────────────────────────────────────────────
        result = provider.send_template(phone, template_key, variables)

        # ── Persist audit record ──────────────────────────────────────────────
        msg_id = f"msg_{uuid4().hex[:8]}"
        stored_variables = dict(variables)
        if result.get("error"):
            stored_variables["_wati_error"] = result["error"]  # persist Wati error for debugging
        db.add(Message(
            id=msg_id,
            contact_id=enr.contact_id,
            template_key=template_key,
            variables=stored_variables,
            provider_message_id=result.get("provider_message_id"),
            status=result.get("status", "queued"),
            provider=result.get("provider", "mock"),
        ))

        # ── Step progression ──────────────────────────────────────────────────
        # NOTE (H4): The Wati API returns "queued" synchronously even when Meta
        # will later reject the template (e.g. MARKETING to a US/CA +1 number).
        # The async delivery failure arrives as a Wati delivery-status webhook
        # that this platform does not yet handle.  As a result, a contact whose
        # template is rejected by Meta still advances to the next step and will
        # NOT receive the message they missed.
        # Mitigation: the /admin/repair/usca-resend endpoint can re-send to stuck
        # contacts.  A future delivery-status webhook handler would fix this
        # structurally.
        if result.get("status", "queued") != "failed":
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


@router.post("/broadcast")
def broadcast_campaign(payload: BroadcastRequest, db: Session = Depends(get_db)):
    """
    Send a message to every contact enrolled in campaign_key / cohort at their current journey step.

    When `edition_key` is provided, the broadcast is constrained to that single
    edition. This keeps the database as the source of truth for campaign
    orchestration and prevents cross-edition leakage.
    """
    edition: ChallengeEdition | None = None
    local_day: date | None = None
    if payload.edition_key:
        edition = (
            db.query(ChallengeEdition)
            .filter(ChallengeEdition.edition_key == payload.edition_key)
            .first()
        )
        if edition:
            local_day = _local_broadcast_date(edition.cohort)
            if _broadcast_already_recorded(db, edition.edition_key, local_day):
                return {
                    "queued": 0,
                    "skipped_no_consent": 0,
                    "skipped_paid_offer": 0,
                    "messages": [],
                    "skipped_already_broadcast": True,
                    "local_date": local_day.isoformat(),
                }

    result = broadcast_campaign_impl(
        db,
        campaign_key=payload.campaign_key,
        cohort=payload.cohort,
        edition_key=payload.edition_key,
        scheduled_local_date=local_day,
    )
    if edition and local_day:
        _record_manual_broadcast_audit(db, edition, local_day, result)
    return result


@router.post("/trigger/day3-offer")
def trigger_day3_offer(payload: Day3OfferRequest, db: Session = Depends(get_db)):
    """Manually send the H+2 Day-3 payment link to StreamYard-registered prospects.

    Filters enrolled contacts to those who have a `day2_streamyard_registered`
    OR `day3_streamyard_registered` ScoreEvent.  Day-2 registrants are accepted
    because Day-3 StreamYard data is not uploaded until after the live ends, and
    the offer fires 2 hours in — before the operator can upload Day-3 data.

    Writes a timed_reminder AuditEvent (same key as the heartbeat path) so that
    if the heartbeat fires at H+2 after a manual trigger, it skips the batch and
    does not double-send.

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
    _BASE_OFFER_TEMPLATE = "live_day3_offer_hplus2"  # constant — never mutated in loop
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

        # Send to contacts who registered on StreamYard for Day 2 OR Day 3.
        # Day-3 data isn't uploaded until after the live; accepting Day-2
        # registrants ensures the 61 already-recorded contacts receive the offer.
        registered = (
            db.query(ScoreEvent)
            .filter(
                ScoreEvent.contact_id == enr.contact_id,
                ScoreEvent.event_type.in_([
                    "day2_streamyard_registered",
                    "day3_streamyard_registered",
                ]),
            )
            .first()
        )
        if not registered:
            skipped_not_registered += 1
            continue

        contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
        phone = contact.phone if contact else enr.contact_id
        first_name = contact.first_name if contact else ""

        # US/CA UTILITY routing — resolve fresh per contact from base template
        template_key = resolve_template_key(_BASE_OFFER_TEMPLATE, phone)

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
        if result.get("status", "queued") != "failed":
            sent += 1

    # Write AuditEvent so the heartbeat's h_plus_2 window is idempotent even
    # if this manual endpoint is called first.
    if payload.edition_key:
        audit_id = f"{payload.edition_key}:day3:h_plus_2"
        already = (
            db.query(AuditEvent)
            .filter(AuditEvent.name == "timed_reminder", AuditEvent.aggregate_id == audit_id)
            .first()
        )
        if not already:
            db.add(AuditEvent(
                name="timed_reminder",
                aggregate_id=audit_id,
                payload={"dispatched": sent, "timing": "h_plus_2", "day": 3, "source": "manual_api"},
            ))

    db.commit()
    return {
        "sent": sent,
        "skipped_no_consent": skipped_no_consent,
        "skipped_not_registered": skipped_not_registered,
        "skipped_paid_offer": skipped_paid_offer,
        "template_key": _BASE_OFFER_TEMPLATE,
    }


# ── Admin repair endpoint ─────────────────────────────────────────────────────

class RepairUsCARequest(BaseModel):
    edition_key: str
    dry_run: bool = True  # default safe — set false to actually commit


@router.post("/admin/repair/usca-resend")
def admin_repair_usca_resend(payload: RepairUsCARequest, db: Session = Depends(get_db)):
    """Advance stuck US/CA contacts and send them today's message.

    Context: US/CA numbers require UTILITY category templates.  Templates
    for Day 1 (and some post-challenge steps) do not yet have _utility variants
    in Wati.  When Wati rejected those sends, the enrollment step was NOT
    advanced (correct behaviour — failed sends don't progress).  However the
    daily AuditEvent IS recorded, so the heartbeat won't retry those contacts.

    This endpoint:
      1. Finds US/CA contacts enrolled in the edition whose step is behind today.
      2. Advances their step to the expected step for today.
      3. Immediately sends today's template to each (no AuditEvent — targeted send).
      4. Returns a full report.

    Use dry_run=true (default) to preview without committing.
    Use dry_run=false to apply.
    """
    from services.campaigns.app.utils import _is_us_ca_phone

    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == payload.edition_key)
        .first()
    )
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    cohort_config = get_cohort_config(edition.cohort)
    tz = ZoneInfo(cohort_config["timezone"])
    local_today = datetime.now(tz).date()
    edition_day = date.fromisoformat(edition.edition_date)
    days_since_start = (local_today - edition_day).days

    # Determine expected step for today using the module-level offset table
    expected_step_key: str | None = None
    for sk, offset in _SCHEDULED_STEP_OFFSETS.items():
        if offset == days_since_start:
            expected_step_key = sk
            break

    if not expected_step_key:
        return {
            "error": f"No journey step scheduled on day offset {days_since_start}",
            "edition_key": payload.edition_key,
            "local_today": local_today.isoformat(),
            "days_since_start": days_since_start,
        }

    expected_step_idx = next(
        (i for i, s in enumerate(DEFAULT_JOURNEY) if s.step_key == expected_step_key),
        None,
    )
    if expected_step_idx is None:
        return {"error": f"Step {expected_step_key} not found in DEFAULT_JOURNEY"}

    enrollments = (
        db.query(CampaignEnrollment)
        .filter(CampaignEnrollment.edition_key == payload.edition_key)
        .all()
    )

    provider = _get_provider()
    repaired: list[dict] = []
    skipped: list[dict] = []

    for enr in enrollments:
        contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
        phone = contact.phone if contact else enr.contact_id

        if not _is_us_ca_phone(phone):
            skipped.append({"contact_id": enr.contact_id, "reason": "not_usca"})
            continue

        current_step_idx = next(
            (i for i, s in enumerate(DEFAULT_JOURNEY) if s.step_key == enr.current_step),
            None,
        )
        if current_step_idx is None:
            skipped.append({"contact_id": enr.contact_id, "reason": "unknown_step", "step": enr.current_step})
            continue
        if current_step_idx >= expected_step_idx:
            skipped.append({"contact_id": enr.contact_id, "reason": "already_current", "step": enr.current_step})
            continue

        # Consent gate
        consent = (
            db.query(Consent)
            .filter(Consent.contact_id == enr.contact_id, Consent.status == "opted_in")
            .first()
        )
        if not consent:
            skipped.append({"contact_id": enr.contact_id, "reason": "no_consent"})
            continue

        step = DEFAULT_JOURNEY[expected_step_idx]
        first_name = contact.first_name if contact else ""

        # 3-way branching (same logic as broadcast_campaign_impl)
        base_template_key = step.template_key
        if step.attendance_event:
            attended = (
                db.query(ScoreEvent)
                .filter(ScoreEvent.contact_id == enr.contact_id, ScoreEvent.event_type == step.attendance_event)
                .first()
            )
            if not attended and step.registration_event:
                registered = (
                    db.query(ScoreEvent)
                    .filter(ScoreEvent.contact_id == enr.contact_id, ScoreEvent.event_type == step.registration_event)
                    .first()
                )
                if registered and step.registered_absent_template_key:
                    base_template_key = step.registered_absent_template_key
                elif step.no_show_template_key:
                    base_template_key = step.no_show_template_key
            elif not attended and step.no_show_template_key:
                base_template_key = step.no_show_template_key

        effective_template = resolve_template_key(base_template_key, phone)
        variables = _build_variables(first_name, effective_template, edition, enr.cohort)

        send_result: dict = {"status": "dry_run", "template_key": effective_template}
        if not payload.dry_run:
            send_result = provider.send_template(phone, effective_template, variables)
            if send_result.get("status") != "failed":
                enr.current_step = (
                    DEFAULT_JOURNEY[expected_step_idx + 1].step_key
                    if expected_step_idx + 1 < len(DEFAULT_JOURNEY)
                    else "completed"
                )
            db.add(Message(
                id=f"msg_{uuid4().hex[:8]}",
                contact_id=enr.contact_id,
                template_key=effective_template,
                variables=variables,
                provider_message_id=send_result.get("provider_message_id"),
                status=send_result.get("status", "queued"),
                provider=send_result.get("provider", "mock"),
            ))

        repaired.append({
            "contact_id": enr.contact_id,
            "old_step": enr.current_step if payload.dry_run else DEFAULT_JOURNEY[current_step_idx].step_key,
            "expected_step": expected_step_key,
            "template_sent": effective_template,
            "send_status": send_result.get("status", "dry_run"),
            "phone_prefix": phone[:5] + "***",
        })

    if not payload.dry_run:
        db.commit()

    return {
        "edition_key": payload.edition_key,
        "local_today": local_today.isoformat(),
        "expected_step": expected_step_key,
        "dry_run": payload.dry_run,
        "repaired_count": len(repaired),
        "skipped_count": len(skipped),
        "repaired": repaired,
        "skipped_summary": {
            reason: sum(1 for s in skipped if s.get("reason") == reason)
            for reason in {s.get("reason") for s in skipped}
        },
    }


app = FastAPI()
app.include_router(router)
