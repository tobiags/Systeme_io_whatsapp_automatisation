"""Admin endpoints — diagnostics and contact recovery.

All endpoints are protected by the standard X-API-Key middleware.

Endpoints
---------
GET  /admin/diagnostics
    Returns a snapshot of the DB state: contacts, enrollments, consents,
    recent message statuses.  Useful to quickly spot why broadcasts reach
    only a subset of contacts.

POST /admin/re-enroll
    Finds every contact that has an opted_in consent record but NO enrollment
    for the given edition, then enrolls them at the correct journey step.
    Idempotent — already-enrolled contacts are skipped.

POST /admin/reset-broadcast-lock
    Deletes the AuditEvent idempotency record that prevents a second broadcast
    on the same edition+day.  Use this when the first broadcast failed or
    reached too few contacts and you need to re-run it on the same calendar day.

POST /admin/advance-step
    Force-advances contacts from one journey step to another for a given edition.
    Use this when contacts are stuck at a step due to provider failures
    (e.g. Meta blocking MARKETING templates for US/CA recipients).
    Example: move contacts stuck at DAY_2 → DAY_3 before the next day's broadcast.
    Supports dry_run to preview the operation without writing.
"""
from __future__ import annotations

from datetime import date, timedelta, timezone, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import (
    AuditEvent,
    CampaignEnrollment,
    ChallengeEdition,
    Consent,
    Contact,
    Message,
)
from shared.db.session import get_db
from services.campaigns.app.rules import DEFAULT_JOURNEY

router = APIRouter(prefix="/admin")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_post_welcome_step(days_until_challenge: int) -> str:
    """Return the next broadcast step after the immediate welcome was sent."""
    if days_until_challenge <= 0:
        return "DAY_1"
    return "COUNTDOWN_J1"


# ── GET /admin/diagnostics ────────────────────────────────────────────────────

@router.get("/diagnostics")
def diagnostics(db: Session = Depends(get_db)):
    """Return a quick snapshot of contacts, enrollments, consents and
    recent message statuses to help identify why broadcasts are partial."""

    total_contacts = db.query(Contact).count()
    total_consents_opted_in = (
        db.query(Consent).filter(Consent.status == "opted_in").count()
    )
    total_enrollments = db.query(CampaignEnrollment).count()

    # Contacts with consent but without ANY enrollment
    consented_ids = {
        r.contact_id
        for r in db.query(Consent.contact_id).filter(Consent.status == "opted_in").all()
    }
    enrolled_ids = {
        r.contact_id for r in db.query(CampaignEnrollment.contact_id).all()
    }
    orphan_count = len(consented_ids - enrolled_ids)

    # Recent message statuses (last 500 messages)
    recent_messages = (
        db.query(Message.status, Message.provider)
        .order_by(Message.created_at.desc())
        .limit(500)
        .all()
    )
    status_counts: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    for msg_status, provider in recent_messages:
        status_counts[msg_status] = status_counts.get(msg_status, 0) + 1
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

    # Active editions
    today = date.today()
    window_start = (today - timedelta(days=6)).isoformat()
    window_end = (today + timedelta(days=90)).isoformat()
    active_editions = (
        db.query(ChallengeEdition)
        .filter(
            ChallengeEdition.edition_date >= window_start,
            ChallengeEdition.edition_date <= window_end,
        )
        .all()
    )

    edition_summaries = []
    for ed in active_editions:
        enr_count = (
            db.query(CampaignEnrollment)
            .filter(CampaignEnrollment.edition_key == ed.edition_key)
            .count()
        )
        # Contacts with consent but not enrolled for THIS edition
        edition_consented = (
            db.query(Consent.contact_id)
            .filter(Consent.status == "opted_in")
            .all()
        )
        edition_consented_ids = {r.contact_id for r in edition_consented}
        edition_enrolled_ids = {
            r.contact_id
            for r in db.query(CampaignEnrollment.contact_id)
            .filter(CampaignEnrollment.edition_key == ed.edition_key)
            .all()
        }
        orphan_for_edition = len(edition_consented_ids - edition_enrolled_ids)

        # Today's broadcast audit
        today_audit = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.name == "campaign_daily_broadcast",
                AuditEvent.aggregate_id == f"{ed.edition_key}:{today.isoformat()}",
            )
            .first()
        )

        # Per-step enrollment breakdown (shows where contacts are stuck)
        step_counts: dict[str, int] = {}
        for enr_row in (
            db.query(CampaignEnrollment.current_step)
            .filter(CampaignEnrollment.edition_key == ed.edition_key)
            .all()
        ):
            s = enr_row.current_step or "unknown"
            step_counts[s] = step_counts.get(s, 0) + 1

        edition_summaries.append({
            "edition_key": ed.edition_key,
            "cohort": ed.cohort,
            "edition_date": ed.edition_date,
            "enrollments": enr_count,
            "contacts_with_consent_not_enrolled": orphan_for_edition,
            "broadcast_already_run_today": today_audit is not None,
            "broadcast_payload": today_audit.payload if today_audit else None,
            "enrollments_by_step": step_counts,
        })

    return {
        "today": today.isoformat(),
        "total_contacts": total_contacts,
        "total_consents_opted_in": total_consents_opted_in,
        "total_enrollments": total_enrollments,
        "contacts_with_consent_but_no_enrollment": orphan_count,
        "recent_500_messages": {
            "by_status": status_counts,
            "by_provider": provider_counts,
        },
        "active_editions": edition_summaries,
    }


# ── POST /admin/re-enroll ─────────────────────────────────────────────────────

class ReEnrollRequest(BaseModel):
    edition_key: str
    cohort: str
    campaign_key: str = "challenge-amazon-fba"
    dry_run: bool = False


@router.post("/re-enroll")
def re_enroll_orphan_contacts(payload: ReEnrollRequest, db: Session = Depends(get_db)):
    """Enroll every contact with opted_in consent that is not yet enrolled
    for the given edition.

    This is the recovery tool for the bug where contacts who registered
    before the edition was created (or after the challenge started) never
    got an enrollment record.

    Pass `dry_run: true` to see what would be enrolled without writing anything.
    """
    # Verify edition exists
    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == payload.edition_key)
        .first()
    )
    if not edition:
        raise HTTPException(
            status_code=404,
            detail=f"Edition '{payload.edition_key}' not found. Create it first via POST /ops/streamyard/session.",
        )

    # Contacts already enrolled in this edition
    already_enrolled_ids = {
        r.contact_id
        for r in db.query(CampaignEnrollment.contact_id)
        .filter(CampaignEnrollment.edition_key == payload.edition_key)
        .all()
    }

    # Contacts with opted_in consent
    consented_contacts = (
        db.query(Consent.contact_id)
        .filter(Consent.status == "opted_in")
        .all()
    )
    consented_ids = {r.contact_id for r in consented_contacts}

    orphan_ids = consented_ids - already_enrolled_ids

    if not orphan_ids:
        return {
            "enrolled": 0,
            "already_enrolled": len(already_enrolled_ids),
            "dry_run": payload.dry_run,
            "message": "All contacts with consent are already enrolled.",
        }

    # Compute step based on days until challenge
    today = date.today()
    try:
        edition_date = date.fromisoformat(edition.edition_date)
    except ValueError:
        raise HTTPException(status_code=500, detail=f"Invalid edition_date '{edition.edition_date}'")

    days_until = (edition_date - today).days
    start_step = _compute_post_welcome_step(days_until)

    enrolled = []
    for contact_id in orphan_ids:
        if payload.dry_run:
            enrolled.append({
                "contact_id": contact_id,
                "start_step": start_step,
                "dry_run": True,
            })
            continue

        enrollment = CampaignEnrollment(
            id=f"enr_{uuid4().hex[:8]}",
            contact_id=contact_id,
            campaign_key=payload.campaign_key,
            edition_key=payload.edition_key,
            current_step=start_step,
            cohort=payload.cohort,
        )
        db.add(enrollment)
        enrolled.append({
            "contact_id": contact_id,
            "enrollment_id": enrollment.id,
            "start_step": start_step,
        })

    if not payload.dry_run:
        db.commit()

    return {
        "enrolled": len(enrolled),
        "already_enrolled": len(already_enrolled_ids),
        "start_step": start_step,
        "days_until_challenge": days_until,
        "dry_run": payload.dry_run,
        "contacts": enrolled,
    }


# ── POST /admin/reset-broadcast-lock ─────────────────────────────────────────

class ResetBroadcastLockRequest(BaseModel):
    edition_key: str
    local_date: str | None = None   # ISO format "YYYY-MM-DD", defaults to today


@router.post("/reset-broadcast-lock")
def reset_broadcast_lock(payload: ResetBroadcastLockRequest, db: Session = Depends(get_db)):
    """Delete the broadcast idempotency lock for an edition+day.

    Use this when the first broadcast reached too few contacts (e.g. because
    most contacts had no enrollment) and you need to re-run it on the same
    calendar day after running /admin/re-enroll.
    """
    lock_date = payload.local_date or date.today().isoformat()
    aggregate_id = f"{payload.edition_key}:{lock_date}"

    audit_row = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.name == "campaign_daily_broadcast",
            AuditEvent.aggregate_id == aggregate_id,
        )
        .first()
    )
    if not audit_row:
        return {
            "deleted": False,
            "aggregate_id": aggregate_id,
            "message": "No broadcast lock found for this edition+date. Nothing to reset.",
        }

    db.delete(audit_row)
    db.commit()
    return {
        "deleted": True,
        "aggregate_id": aggregate_id,
        "message": (
            f"Broadcast lock removed for {aggregate_id}. "
            "You can now re-run POST /campaigns/broadcast for this edition."
        ),
    }


# ── POST /admin/advance-step ──────────────────────────────────────────────────

class AdvanceStepRequest(BaseModel):
    edition_key: str
    from_step: str
    to_step: str
    dry_run: bool = False


@router.post("/advance-step")
def advance_step(payload: AdvanceStepRequest, db: Session = Depends(get_db)):
    """Force-advance contacts from one journey step to another.

    Use this when contacts are stuck at a step due to provider failures
    (e.g. Meta blocking MARKETING templates for US/CA recipients).

    Typical recovery flow when UTILITY templates are not yet approved:
      1. POST /admin/advance-step  from_step=DAY_2  to_step=DAY_3
      2. POST /campaigns/broadcast (Day 3 now reaches all contacts)

    When UTILITY templates ARE approved and you want to retry the missed day:
      1. POST /admin/reset-broadcast-lock  (clear today's idempotency lock)
      2. POST /campaigns/broadcast         (retries DAY_2 for stuck contacts only;
         contacts already at DAY_3 are skipped by the date-gate in broadcast logic)

    Pass `dry_run: true` to preview how many contacts would be advanced.
    """
    valid_steps = {s.step_key for s in DEFAULT_JOURNEY} | {"completed"}
    if payload.from_step not in valid_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid from_step '{payload.from_step}'. Valid: {sorted(valid_steps)}",
        )
    if payload.to_step not in valid_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid to_step '{payload.to_step}'. Valid: {sorted(valid_steps)}",
        )

    enrollments = (
        db.query(CampaignEnrollment)
        .filter(
            CampaignEnrollment.edition_key == payload.edition_key,
            CampaignEnrollment.current_step == payload.from_step,
        )
        .all()
    )

    if not enrollments:
        return {
            "advanced": 0,
            "from_step": payload.from_step,
            "to_step": payload.to_step,
            "edition_key": payload.edition_key,
            "dry_run": payload.dry_run,
            "message": f"No enrollments at step '{payload.from_step}' for edition '{payload.edition_key}'.",
        }

    contact_ids = []
    for enr in enrollments:
        contact_ids.append(enr.contact_id)
        if not payload.dry_run:
            enr.current_step = payload.to_step

    if not payload.dry_run:
        db.commit()

    verb = "Would advance" if payload.dry_run else "Advanced"
    return {
        "advanced": len(contact_ids),
        "from_step": payload.from_step,
        "to_step": payload.to_step,
        "edition_key": payload.edition_key,
        "dry_run": payload.dry_run,
        "contact_ids": contact_ids,
        "message": f"{verb} {len(contact_ids)} contacts from '{payload.from_step}' → '{payload.to_step}'.",
    }
