"""Celery task: sync Systeme.io contacts daily by challenge tag.

Runs automatically every 24h via Celery Beat (configured in celery_app.py).
Can also be triggered manually from the OPS page.

Tag → cohort mapping:
  "CHALLENGE US/CA"  →  US-CA
  "CHALLENGE EU"     →  EU
"""
from __future__ import annotations

import logging
import re
from uuid import uuid4

import httpx

from services.campaigns.app.celery_app import celery_app
from shared.db.session import get_engine_and_session

logger = logging.getLogger(__name__)

_SYSTEMEIO_API_BASE = "https://api.systeme.io/api"

# Hard cap on pagination — observed 2026-06-10: the API kept returning full
# pages past page 32 000 (3.3M rows for an account with a few thousand
# contacts), so the while-loop never terminated and saturated both worker
# processes for hours, blocking the daily broadcast.
_MAX_PAGES = 300  # 300 × 100 = 30 000 contacts max per sync run

_TAG_COHORT_MAP: dict[str, str] = {
    "challenge us/ca": "US-CA",
    "challenge eu":    "EU",
}


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    phone = re.sub(r"[\s\-\.\(\)]", "", raw.strip())
    if phone.startswith("+"):
        phone = phone[1:]
    elif phone.startswith("00"):
        phone = phone[2:]
    return phone or None


def _run_sync(api_key: str) -> dict:
    """Core sync logic — usable both from Celery task and from HTTP endpoint."""
    from shared.db.models import CampaignEnrollment, ChallengeEdition, Consent, Contact, ScoreEvent
    from datetime import date, timedelta

    results = {"created": 0, "updated": 0, "skipped": 0, "errors": 0, "total_fetched": 0}
    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()

    try:
        page = 1
        has_more = True
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

        with httpx.Client(timeout=30, headers=headers) as client:
            while has_more:
                if page > _MAX_PAGES:
                    logger.error(
                        "Systeme.io sync aborted at page cap (%d pages, %d fetched) — "
                        "API pagination did not terminate",
                        _MAX_PAGES, results["total_fetched"],
                    )
                    break
                resp = client.get(
                    f"{_SYSTEMEIO_API_BASE}/contacts",
                    params={"page": page, "limit": 100},
                )
                if resp.status_code != 200:
                    logger.error("Systeme.io API %s: %s", resp.status_code, resp.text[:200])
                    break

                data = resp.json()
                items: list = (
                    data.get("items")
                    or data.get("data")
                    or (data if isinstance(data, list) else [])
                )
                total = data.get("totalItems") or data.get("total") or 0
                results["total_fetched"] += len(items)
                has_more = bool(items) and len(items) == 100 and (total == 0 or results["total_fetched"] < total)
                page += 1

                for contact_data in items:
                    # ── Tag → cohort ──────────────────────────────────────────
                    tags: list = contact_data.get("tags") or []
                    tag_names = [
                        (t.get("name") or t.get("tag") or "").lower().strip()
                        for t in tags
                    ]
                    cohort = next(
                        (v for k, v in _TAG_COHORT_MAP.items() if k in tag_names),
                        None,
                    )
                    if not cohort:
                        continue

                    # ── Extract fields ────────────────────────────────────────
                    raw_fields = contact_data.get("fields") or []
                    if isinstance(raw_fields, list):
                        fields = {f.get("slug", ""): f.get("value", "") for f in raw_fields}
                    elif isinstance(raw_fields, dict):
                        fields = raw_fields
                    else:
                        fields = {}

                    email = (contact_data.get("email") or "").lower().strip()
                    phone = _normalize_phone(fields.get("phone_number") or fields.get("phone"))
                    first_name = (fields.get("first_name") or "").strip() or None

                    if not phone and not email:
                        results["skipped"] += 1
                        continue

                    try:
                        # Savepoint per contact: a UniqueViolation on one contact
                        # must not poison the whole session (observed 2026-06-10:
                        # one duplicate phone → PendingRollbackError on every
                        # subsequent contact → task retry → infinite loop).
                        nested = db.begin_nested()
                        # ── Upsert contact ────────────────────────────────────
                        contact = None
                        if phone:
                            contact = db.query(Contact).filter(Contact.phone == phone).first()
                        if not contact and email:
                            contact = db.query(Contact).filter(Contact.email == email).first()

                        if contact:
                            if first_name and not contact.first_name:
                                contact.first_name = first_name
                            if email and not contact.email:
                                contact.email = email
                            db.flush()
                            results["updated"] += 1
                        else:
                            if not phone:
                                nested.rollback()
                                results["skipped"] += 1
                                continue
                            contact = Contact(
                                id=f"ct_{uuid4().hex[:8]}",
                                phone=phone,
                                email=email or None,
                                first_name=first_name,
                                source="systemeio_sync",
                            )
                            db.add(contact)
                            db.flush()
                            results["created"] += 1

                        # ── Consent ───────────────────────────────────────────
                        if not db.query(Consent).filter(
                            Consent.contact_id == contact.id,
                            Consent.status == "opted_in",
                        ).first():
                            db.add(Consent(
                                contact_id=contact.id,
                                status="opted_in",
                                proof_source="systemeio_tag_sync",
                            ))

                        # ── Auto-enroll in active edition ─────────────────────
                        today = date.today()
                        window_start = (today - timedelta(days=6)).isoformat()
                        active_edition = (
                            db.query(ChallengeEdition)
                            .filter(
                                ChallengeEdition.cohort == cohort,
                                ChallengeEdition.edition_date >= window_start,
                            )
                            .order_by(ChallengeEdition.edition_date.asc())
                            .first()
                        )
                        if active_edition:
                            already_enrolled = db.query(CampaignEnrollment).filter(
                                CampaignEnrollment.contact_id == contact.id,
                                CampaignEnrollment.edition_key == active_edition.edition_key,
                            ).first()
                            if not already_enrolled:
                                from datetime import date as _date
                                edition_day = _date.fromisoformat(active_edition.edition_date)
                                days_until = (edition_day - today).days
                                from services.campaigns.app.rules import compute_start_step
                                step = compute_start_step(days_until)
                                db.add(CampaignEnrollment(
                                    id=f"enr_{uuid4().hex[:8]}",
                                    contact_id=contact.id,
                                    campaign_key=active_edition.campaign_key,
                                    edition_key=active_edition.edition_key,
                                    current_step=step,
                                    cohort=cohort,
                                ))

                        nested.commit()

                    except Exception as exc:
                        logger.error("sync_contact error phone=%s: %s", phone, exc)
                        try:
                            nested.rollback()  # restore session to last good savepoint
                        except Exception:
                            db.rollback()
                        results["errors"] += 1
                        continue

                db.commit()

        logger.info(
            "Systeme.io sync complete: fetched=%d created=%d updated=%d skipped=%d errors=%d",
            results["total_fetched"], results["created"], results["updated"],
            results["skipped"], results["errors"],
        )
        return results

    except Exception as exc:
        logger.error("Systeme.io sync failed: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    name="integrations.sync_systemeio_contacts",
    bind=True,
    max_retries=2,
    # Kill switch: the sync must NEVER run long enough to starve the
    # broadcast heartbeat (observed 2026-06-10: two sync instances ran for
    # 9+ hours, both worker processes saturated, 19:00 broadcast never fired).
    soft_time_limit=1500,   # 25 min — SoftTimeLimitExceeded raised inside task
    time_limit=1560,        # 26 min — hard SIGKILL safety net
)
def sync_systemeio_contacts(self):
    """Daily Celery task: sync Systeme.io contacts tagged with challenge tags."""
    import os
    from services.campaigns.app.utils import redis_lock

    api_key = os.getenv("SYSTEMEIO_API_KEY", "")
    if not api_key:
        logger.warning("sync_systemeio_contacts: SYSTEMEIO_API_KEY not set — skipping")
        return {"skipped": True, "reason": "no_api_key"}

    # Singleton guard: beat schedule + retries must never stack two sync
    # instances — that would occupy both worker processes and block broadcasts.
    with redis_lock("sync_systemeio_lock", timeout=1800) as acquired:
        if not acquired:
            logger.warning("sync_systemeio_contacts: another sync is already running — skipping")
            return {"skipped": True, "reason": "already_running"}
        try:
            return _run_sync(api_key)
        except Exception as exc:
            logger.error("sync_systemeio_contacts failed: %s", exc)
            raise self.retry(exc=exc, countdown=300)
