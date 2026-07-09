from datetime import date, datetime, timezone
import logging
from uuid import uuid4
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

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
from services.campaigns.app.utils import broadcast_already_recorded, broadcast_audit_id, broadcast_lock, resolve_template_key
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
    live_time_label = cohort_cfg.get("live_time_label", live_time)

    # Normalise: strip _utility suffix so pattern matching works identically
    # for both MARKETING and UTILITY variants of the same template.
    base_key = template_key.removesuffix("_utility")

    # countdown_j1_v7: {{2}} = lien StreamYard J1, {{3}} = heure du live
    if base_key == "countdown_j1_v7":
        variables["2"] = (edition.day1_url or edition.streamyard_url or "") if edition else ""
        variables["3"] = live_time_label

    # countdown_j1_v2: {{2}} = heure du live, {{3}} = lien inscription StreamYard J1
    elif base_key in {"countdown_j1", "countdown_j1_v2"}:
        variables["2"] = live_time
        variables["3"] = (edition.day1_url or edition.streamyard_url or "") if edition else ""

    # countdown_j3_v2: {{2}}=lien J1, {{3}}=lien J2, {{4}}=lien J3
    elif base_key in {"countdown_j3", "countdown_j3_v2"}:
        variables["2"] = (edition.day1_url or edition.streamyard_url or "") if edition else ""
        variables["3"] = (edition.day2_url or edition.streamyard_url or "") if edition else ""
        variables["4"] = (edition.day3_url or edition.streamyard_url or "") if edition else ""

    # H+2 and H+3 Day 3 offer (legacy) + H+90 v7 (MARKETING): payment link ({{2}})
    elif base_key in {
        "live_day3_offer", "live_day3_offer_hplus2", "live_day3_offer_hplus3",
        "live_day3_offer_hplus2_v2", "live_day3_offer_hplus3_v2",
        "live_day3_offer_hplus3_v4",
        "live_day3_h90_v7",
    }:
        variables["2"] = (
            (edition.payment_url if edition else None)
            or settings.program_payment_url
            or ""
        )

    # post_replay_v7: {{2}} = lien replay J3 (48h window)
    elif base_key == "post_replay_v7":
        variables["2"] = (
            (edition.replay_day3_url if edition else None)
            or settings.replay_day3_url
            or ""
        )

    # post_recap_registered_absent / post_recap_not_registered:
    #   {{2}} = lien unique replays (page ecommercecentrale.com/replays-challenge)
    #   post_recap_not_registered also gets {{3}} = closer booking URL
    elif base_key in {"post_recap_registered_absent", "post_recap_registered_absent_v2", "post_recap_registered_absent_v4"}:
        variables["2"] = (
            (edition.replay_day3_url if edition else None)
            or settings.replay_day3_url
            or ""
        )
    elif base_key in {"post_recap_not_registered", "post_recap_not_registered_v2", "post_recap_not_registered_v4"}:
        variables["2"] = (
            (edition.replay_day3_url if edition else None)
            or settings.replay_day3_url
            or ""
        )
        variables["3"] = (
            (edition.closer_booking_url if edition else None)
            or settings.oncehub_form_url
            or ""
        )

    # post-challenge closer / booking templates: {{2}} = closer booking URL
    elif base_key in {
        "post_closer_call", "post_closer_call_v2", "post_closer_call_v4", "post_closer_call_v5", "post_closer_call_v7",
        "post_closer_v7",
        "post_followup",
        "post_recap_attended", "post_recap_attended_v2", "post_recap_attended_v4",
    }:
        variables["2"] = (
            (edition.closer_booking_url if edition else None)
            or settings.oncehub_form_url
            or ""
        )

    # post_testimonials_v7: {{2}} = closer booking URL per Wati template body.
    # Legacy post_testimonials variants keep the testimonials-page mapping.
    elif base_key == "post_testimonials_v7":
        variables["2"] = (
            (edition.closer_booking_url if edition else None)
            or settings.oncehub_form_url
            or ""
        )

    # post_testimonials legacy: {{2}} = lien temoignages (configurable per edition)
    elif base_key in {"post_testimonials", "post_testimonials_v2", "post_testimonials_v5"}:
        variables["2"] = (
            (edition.testimonials_url if edition else None)
            or settings.oncehub_form_url.replace("formulaire-challenge", "temoignages")
            or ""
        )

    # post_inaction_reason: only {{1}} = first_name (no URL)
    elif base_key in {"post_inaction_reason", "post_inaction_reason_v2"}:
        pass  # variables already contains {"1": name}

    # live_day3_h2_v7: H-2 reminder — {{2}} = StreamYard J3 only (no {{3}}: 2-param template)
    elif base_key == "live_day3_h2_v7":
        variables["2"] = (edition.day3_url or edition.streamyard_url or "") if edition else ""

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
        variables["3"] = live_time_label

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
    """Record a manual broadcast audit event.

    Uses INSERT … ON CONFLICT DO NOTHING so it's safe to call even if the
    beat already recorded the same edition+date (UNIQUE on aggregate_id).
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(AuditEvent).values(
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
    ).on_conflict_do_nothing(index_elements=["aggregate_id"])
    db.execute(stmt)
    db.commit()


def _auto_advance_stuck_contact(
    enr: "CampaignEnrollment",
    edition: "ChallengeEdition",
    scheduled_local_date: date,
    current_step_idx: int,
) -> bool:
    """Advance a contact stuck at a past step to the step matching today.

    Late enrollees or migrated contacts can be assigned a step whose scheduled date has already passed. This function
    walks forward through DEFAULT_JOURNEY until it finds the step whose offset
    matches `scheduled_local_date`, then updates enr.current_step.

    Returns True if the contact was advanced (caller should re-resolve step),
    False if no matching step was found (contact should be skipped).
    """
    for idx in range(current_step_idx + 1, len(DEFAULT_JOURNEY)):
        candidate = DEFAULT_JOURNEY[idx]
        if _step_is_due_on_local_date(
            candidate.step_key,
            edition.edition_date,
            scheduled_local_date,
        ):
            logger.info(
                "Auto-advancing stuck contact %s from %s to %s (edition=%s, date=%s)",
                enr.contact_id, enr.current_step, candidate.step_key,
                enr.edition_key, scheduled_local_date,
            )
            enr.current_step = candidate.step_key
            return True
    return False


# Offsets in days from edition_date (= Day 1 date).
# DAY_3 = Day 1 + 2, so "J+1 after the challenge" = Day 1 + 3, etc.
_SCHEDULED_STEP_OFFSETS = {
    "COUNTDOWN_J1":  -1,  # J-1 before Day 1
    "DAY_1":          0,  # Day 1 (live)
    "DAY_2":          1,  # Day 2 (live)
    "DAY_3":          2,  # Day 3 (live)
    "AFTER_REPLAY":   3,  # J+1 after challenge (replay 48h) — MARKETING
    "AFTER_1":        4,  # J+2 — testimonials page — MARKETING
    "AFTER_2":        5,  # J+3 — pre-closer message — MARKETING
    "AFTER_3":        6,  # J+4 — closer booking call — MARKETING
}


def _step_is_due_on_local_date(step_key: str, edition_date: str | None, local_day: date | None) -> bool:
    offset = _SCHEDULED_STEP_OFFSETS.get(step_key)
    if offset is None:
        return True  # unscheduled step (WELCOME) — always due
    if not local_day or not edition_date:
        return False  # fail-closed: can't determine schedule without dates
    try:
        edition_day = date.fromisoformat(edition_date)
    except ValueError:
        return False  # fail-closed: malformed date → block rather than send
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
            CampaignEnrollment.current_step != "completed",
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
            # Orphaned step from an older journey — auto-recover
            # to whichever step is due today instead of silently skipping the contact.
            if scheduled_local_date and enr.edition_key:
                edition_for_recovery = (
                    db.query(ChallengeEdition)
                    .filter(ChallengeEdition.edition_key == enr.edition_key)
                    .first()
                )
                if edition_for_recovery:
                    for idx, s in enumerate(DEFAULT_JOURNEY):
                        if s.step_key not in _SCHEDULED_STEP_OFFSETS:
                            continue  # skip unscheduled steps (WELCOME etc.) — they have no date binding
                        if _step_is_due_on_local_date(
                            s.step_key, edition_for_recovery.edition_date, scheduled_local_date
                        ):
                            logger.warning(
                                "Recovering orphaned contact %s from %s → %s (edition=%s)",
                                enr.contact_id, enr.current_step, s.step_key, enr.edition_key,
                            )
                            enr.current_step = s.step_key
                            step_idx = idx
                            break
            if step_idx is None:
                continue

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
            # ── Auto-advance stuck contacts ──────────────────────────────────
            # Late enrollees may be at a step whose scheduled date has already
            # passed.
            # Skip forward until we find the step that matches today, or the
            # first future step.  This ensures late enrollees rejoin the live
            # flow instead of being stuck forever.
            if scheduled_local_date and edition:
                advanced = _auto_advance_stuck_contact(
                    enr, edition, scheduled_local_date, step_idx,
                )
                if not advanced:
                    continue
                # Re-resolve step after advancement
                step_idx = next(
                    (i for i, s in enumerate(DEFAULT_JOURNEY) if s.step_key == enr.current_step),
                    None,
                )
                if step_idx is None:
                    continue
                step = DEFAULT_JOURNEY[step_idx]
            else:
                continue

        # ── Consent gate (spec §4.3) ──────────────────────────────────────────
        # Use the LATEST consent record — a later opted_out (STOP) must block
        # even if an older opted_in record exists in the journal.
        consent = (
            db.query(Consent)
            .filter(Consent.contact_id == enr.contact_id)
            .order_by(Consent.id.desc())
            .first()
        )
        if not consent or consent.status != "opted_in":
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

    if edition and local_day:
        with broadcast_lock(edition.edition_key, local_day) as acquired:
            if not acquired:
                raise HTTPException(status_code=409, detail="Broadcast already in progress for this edition/day")
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
            _record_manual_broadcast_audit(db, edition, local_day, result)
            return result

    result = broadcast_campaign_impl(
        db,
        campaign_key=payload.campaign_key,
        cohort=payload.cohort,
        edition_key=payload.edition_key,
        scheduled_local_date=local_day,
    )
    return result


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

        # Consent gate — latest record wins (STOP after opt-in must block)
        consent = (
            db.query(Consent)
            .filter(Consent.contact_id == enr.contact_id)
            .order_by(Consent.id.desc())
            .first()
        )
        if not consent or consent.status != "opted_in":
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
