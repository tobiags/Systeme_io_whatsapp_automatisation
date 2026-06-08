"""Celery tasks for timed live-session message dispatch.

Each live day (Day 1, Day 2, Day 3) triggers 3 timed reminders:
  • H-2h   — primary reminder with StreamYard link
  • H-10m  — final countdown reminder                 → live_day{N}_h10
  • H+5m   — late nudge after the live started        → live_day{N}_hplus5

Each task:
  1. Resolves enrolled contacts for the given campaign/cohort/edition.
  2. Looks up Contact (first_name + phone) for each enrollment.
  3. Builds template variables: {{1}} first_name, {{2}} StreamYard URL,
     {{3}} session time.
  4. Calls WatiProvider (real API) or MockProvider (dev/test, no credentials).
  5. Persists a Message audit row with the actual provider status.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import logging
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.campaigns.app.celery_app import celery_app
from services.campaigns.app.challenge_calendar import get_cohort_config
from shared.db.models import AuditEvent, CampaignEnrollment, ChallengeEdition, Consent, Contact, Message, ScoreEvent
from shared.db.session import get_engine_and_session

logger = logging.getLogger(__name__)

# Template key pattern: live_day{N}_{timing}
# h10 / hplus5 use _v4 suffix (Wati blocked _v2 after deletion, then _v3 naming cycle).
# Generated pattern: f"live_day{N}_{suffix}" → e.g. live_day1_h10_v4
_TEMPLATE_MAP: dict[str, str] = {
    "h2":        "h2",
    "h10":       "h10_v4",      # → live_day{N}_h10_v4
    "h_plus_5":  "hplus5_v4",   # → live_day{N}_hplus5_v4
}

# Timings that include the StreamYard live link ({{2}}) + live time ({{3}})
_TIMINGS_WITH_URL = {"h2", "h10", "h_plus_5"}


def _get_provider():
    """Return WatiProvider when credentials are configured, else MockProvider."""
    from shared.config.settings import settings
    from services.messaging.app.providers.mock import MockProvider
    from services.messaging.app.providers.wati import WatiProvider

    if settings.wati_api_url and settings.wati_api_token:
        return WatiProvider(settings.wati_api_url, settings.wati_api_token)
    return MockProvider()


def _build_task_variables(
    first_name: str,
    timing: str,
    streamyard_url: str,
    cohort: str,
) -> dict[str, str]:
    """Build template variables for a timed dispatch task.

    {{1}} — first_name (all timings)
    {{2}} — StreamYard URL
    {{3}} — live session time, e.g. "21:00"
    """
    name = (first_name or "").strip() or "vous"
    variables: dict[str, str] = {"1": name}

    if timing in _TIMINGS_WITH_URL:
        cohort_cfg = get_cohort_config(cohort)
        variables["2"] = streamyard_url or ""
        variables["3"] = cohort_cfg.get("live_time", "21:00")

    return variables


def _resolve_timed_streamyard_url(db, edition_key: str, day_number: int, fallback_url: str) -> str:
    if not edition_key:
        return fallback_url or ""

    edition = (
        db.query(ChallengeEdition)
        .filter(ChallengeEdition.edition_key == edition_key)
        .first()
    )
    if not edition:
        return fallback_url or ""

    day_url = {
        1: edition.day1_url,
        2: edition.day2_url,
        3: edition.day3_url,
    }.get(day_number)
    return day_url or edition.streamyard_url or fallback_url or ""


from services.campaigns.app.utils import broadcast_already_recorded, broadcast_audit_id, resolve_template_key


def _contact_has_paid_offer(contact_id: str, db) -> bool:
    return (
        db.query(ScoreEvent)
        .filter(
            ScoreEvent.contact_id == contact_id,
            ScoreEvent.event_type == "paid_offer",
        )
        .first()
        is not None
    )


def _parse_clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":"))
    return time(hour=hour, minute=minute)


def _edition_is_in_daily_window(edition_date_value: str, local_today: date) -> bool:
    edition_day = date.fromisoformat(edition_date_value)
    start_day = edition_day - timedelta(days=6)
    end_day = edition_day + timedelta(days=7)
    return start_day <= local_today <= end_day


# _broadcast_already_recorded is now in utils.py (single source of truth).
# Local alias for backward-compat with callers in this file.
_broadcast_already_recorded = broadcast_already_recorded


def _try_claim_broadcast_slot(db, edition: ChallengeEdition, local_date: date) -> bool:
    """Atomically claim the broadcast slot for this edition+date.

    Uses INSERT … ON CONFLICT DO NOTHING backed by the UNIQUE constraint on
    aggregate_id.  Returns True if this worker claimed the slot (i.e. should
    proceed to send), False if another worker already claimed it.

    This replaces the old SELECT-then-INSERT pattern which had a TOCTOU race
    when two Celery workers ran the same task concurrently.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.exc import IntegrityError

    aggregate_id = f"{edition.edition_key}:{local_date.isoformat()}"
    try:
        stmt = pg_insert(AuditEvent).values(
            name="campaign_daily_broadcast",
            aggregate_id=aggregate_id,
            payload={
                "campaign_key": edition.campaign_key,
                "cohort": edition.cohort,
                "edition_key": edition.edition_key,
                "local_date": local_date.isoformat(),
                "status": "pending",
            },
        ).on_conflict_do_nothing(index_elements=["aggregate_id"])
        result = db.execute(stmt)
        db.commit()
        return result.rowcount == 1  # 1 = we inserted, 0 = already existed
    except IntegrityError:
        db.rollback()
        return False


def _update_broadcast_audit(db, edition: ChallengeEdition, local_date: date, payload: dict) -> None:
    """Update the audit record written by _try_claim_broadcast_slot with final counts."""
    aggregate_id = f"{edition.edition_key}:{local_date.isoformat()}"
    event = db.query(AuditEvent).filter(AuditEvent.aggregate_id == aggregate_id).first()
    if event:
        event.payload = {
            "campaign_key": edition.campaign_key,
            "cohort": edition.cohort,
            "edition_key": edition.edition_key,
            "local_date": local_date.isoformat(),
            **payload,
        }
        db.commit()


def _record_broadcast_audit(db, edition: ChallengeEdition, local_today: date, payload: dict) -> None:
    """Legacy helper kept for callers outside dispatch_daily_broadcasts."""
    _try_claim_broadcast_slot(db, edition, local_today)
    _update_broadcast_audit(db, edition, local_today, payload)


def _resolve_timed_template_key(day_number: int, timing: str, contact_id: str, db) -> str:
    """Resolve the timed reminder template for a contact.

    H-10 and H+5: generic day-level templates for all contacts (no branching).
    H-2 (h2): unified template for all contacts — same "session starts soon"
    reminder regardless of prior attendance. All day-2/3 contacts receive
    live_day{N}_attended_v2 at H-2 for a consistent, welcoming tone.
    """
    suffix = _TEMPLATE_MAP[timing]
    if timing != "h2" or day_number == 1:
        return f"live_day{day_number}_{suffix}"

    # H-2 Day 2 & 3: unified reminder for ALL contacts (no behavioral branching).
    # Client decision: same template regardless of prior-day attendance.
    if day_number == 2:
        return "live_day2_attended_v3"
    if day_number == 3:
        return "live_day3_attended_v3"

    return f"live_day{day_number}_{suffix}"


def _dispatch_messages_for_cohort(
    campaign_key: str,
    cohort: str,
    day_number: int,
    edition_key: str,
    timing: str,
    streamyard_url: str,
) -> int:
    """Send template messages to every enrolled contact in the given cohort.

    Returns the number of messages successfully dispatched.
    """
    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()
    try:
        provider = _get_provider()
        resolved_streamyard_url = _resolve_timed_streamyard_url(
            db,
            edition_key=edition_key,
            day_number=day_number,
            fallback_url=streamyard_url,
        )

        enrollments = (
            db.query(CampaignEnrollment)
            .filter(
                CampaignEnrollment.campaign_key == campaign_key,
                CampaignEnrollment.cohort == cohort,
                *(
                    [CampaignEnrollment.edition_key == edition_key]
                    if edition_key
                    else []
                ),
            )
            .all()
        )

        count = 0
        for enr in enrollments:
            consent = (
                db.query(Consent)
                .filter(Consent.contact_id == enr.contact_id, Consent.status == "opted_in")
                .first()
            )
            if not consent:
                continue

            if _contact_has_paid_offer(enr.contact_id, db):
                continue

            template_key = _resolve_timed_template_key(
                day_number=day_number,
                timing=timing,
                contact_id=enr.contact_id,
                db=db,
            )

            # Look up Contact for first_name + phone
            contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
            phone = contact.phone if contact else enr.contact_id
            first_name = contact.first_name if contact else ""

            # US/CA UTILITY routing — only when _utility variant exists in Wati
            template_key = resolve_template_key(template_key, phone)

            # ── Deduplication guard ───────────────────────────────────────────
            # Skip if this exact template was already sent to this contact
            # within the last 12 hours (prevents H-2 from duplicating the
            # morning broadcast when both use the same behavioural template).
            from datetime import timezone as _tz
            cutoff = datetime.now(_tz.utc) - timedelta(hours=12)
            already_sent = (
                db.query(Message)
                .filter(
                    Message.contact_id == enr.contact_id,
                    Message.template_key == template_key,
                    Message.created_at >= cutoff,
                )
                .first()
            )
            if already_sent:
                logger.debug(
                    "Skipping duplicate %s → %s (already sent at %s)",
                    enr.contact_id, template_key, already_sent.created_at,
                )
                continue

            variables = _build_task_variables(
                first_name=first_name,
                timing=timing,
                streamyard_url=resolved_streamyard_url,
                cohort=cohort,
            )

            # Call the real provider (WatiProvider in prod, MockProvider in dev)
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
                count += 1

        db.commit()
        return count

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Generic task factory ──────────────────────────────────────────────────────

def _make_dispatch_task(timing: str):
    """Return a Celery task that dispatches <timing> messages for a live day."""

    @celery_app.task(name=f"campaigns.dispatch_{timing}", bind=True, max_retries=3)
    def _task(
        self,
        campaign_key: str,
        cohort: str,
        day_number: int,
        edition_key: str = "",
        streamyard_url: str = "",
    ):
        logger.info(
            "Dispatching %s for campaign=%s cohort=%s day=%d edition=%s url=%s",
            timing, campaign_key, cohort, day_number, edition_key,
            "set" if streamyard_url else "empty",
        )
        try:
            count = _dispatch_messages_for_cohort(
                campaign_key=campaign_key,
                cohort=cohort,
                day_number=day_number,
                edition_key=edition_key,
                timing=timing,
                streamyard_url=streamyard_url,
            )
            logger.info("Dispatched %d messages for day=%d timing=%s", count, day_number, timing)
            return {"dispatched": count, "day_number": day_number, "timing": timing}
        except Exception as exc:
            logger.error("Task %s failed: %s", self.name, exc)
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    return _task


# ── Exported tasks ────────────────────────────────────────────────────────────

dispatch_h2    = _make_dispatch_task("h2")
dispatch_h10   = _make_dispatch_task("h10")
dispatch_h_plus_5 = _make_dispatch_task("h_plus_5")


# ── Auto-broadcast task (triggered by ops page submission) ────────────────────

@celery_app.task(name="campaigns.dispatch_broadcast", bind=True, max_retries=2)
def dispatch_broadcast(self, campaign_key: str, cohort: str, edition_key: str, local_date_str: str):
    """Automated daily broadcast triggered automatically from the ops/streamyard page.

    Calls broadcast_campaign_impl directly — no HTTP overhead, same process.
    Scheduled at H-8 before the live; fires immediately if ops page submitted late.

    IDEMPOTENCY: Checks AuditEvent before calling broadcast_campaign_impl to prevent
    double-sends when the heartbeat (dispatch_daily_broadcasts) already fired the
    same broadcast at 09:00 local time.
    """
    from datetime import date as _date

    local_date = _date.fromisoformat(local_date_str)
    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()
    try:
        # ── Idempotency guard ─────────────────────────────────────────────────
        # dispatch_daily_broadcasts (heartbeat) fires at 09:00 local time and
        # records an AuditEvent. If this task fires AFTER that heartbeat, the
        # broadcast is already done — skip to avoid advancing enrollment steps
        # a second time and sending Day N+1 messages on the same day.
        if _broadcast_already_recorded(db, edition_key, local_date):
            logger.info(
                "dispatch_broadcast skipped (already done by heartbeat): edition=%s date=%s",
                edition_key, local_date_str,
            )
            return {"queued": 0, "skipped_already_broadcast": True}

        # Lazy import to avoid circular dependency with main.py
        from services.campaigns.app.main import broadcast_campaign_impl
        result = broadcast_campaign_impl(
            db,
            campaign_key=campaign_key,
            cohort=cohort,
            edition_key=edition_key,
            scheduled_local_date=local_date,
        )
        queued = result.get("queued", 0)

        # Record the AuditEvent so the heartbeat won't re-fire it
        edition = db.query(ChallengeEdition).filter(
            ChallengeEdition.edition_key == edition_key
        ).first()
        if edition:
            _record_broadcast_audit(db, edition, local_date, result)

        logger.info(
            "dispatch_broadcast complete: edition=%s date=%s queued=%d",
            edition_key, local_date_str, queued,
        )
        return result
    except Exception as exc:
        logger.error("dispatch_broadcast failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


# ── H+2 Day-3 offer (special task — filters by StreamYard registration) ───────

def _dispatch_day3_offer(campaign_key: str, cohort: str, edition_key: str) -> int:
    """Send live_day3_offer_hplus2 to contacts who registered for Day 3 on StreamYard.

    Applies the consent gate + day3_streamyard_registered filter.
    Returns the number of messages dispatched.
    """
    from shared.config.settings import settings

    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()
    try:
        provider = _get_provider()

        query = db.query(CampaignEnrollment).filter(
            CampaignEnrollment.campaign_key == campaign_key,
            CampaignEnrollment.cohort == cohort,
        )
        if edition_key:
            query = query.filter(CampaignEnrollment.edition_key == edition_key)
        enrollments = query.all()

        template_key = "live_day3_offer_hplus2_v2"
        edition = None
        if edition_key:
            edition = (
                db.query(ChallengeEdition)
                .filter(ChallengeEdition.edition_key == edition_key)
                .first()
            )

        count = 0
        for enr in enrollments:
            # Consent gate
            consent = (
                db.query(Consent)
                .filter(Consent.contact_id == enr.contact_id, Consent.status == "opted_in")
                .first()
            )
            if not consent:
                continue

            if _contact_has_paid_offer(enr.contact_id, db):
                continue

            # Filter: contacts who registered on StreamYard for Day 2 OR Day 3.
            # Day 2 registrants are uploaded before the Day 3 broadcast (61 contacts
            # as of 2026-05-30).  Day 3 registrants are uploaded after Day 3's live —
            # the idempotency guard on AuditEvent prevents double-sends.
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
                continue

            contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
            phone = contact.phone if contact else enr.contact_id
            first_name = (contact.first_name or "").strip() if contact else ""
            name = first_name or "vous"

            # Apply US/CA → _utility routing (MARKETING blocked by Meta for +1 numbers)
            effective_template = resolve_template_key(template_key, phone)

            # 12-hour dedup guard — prevents double-send on partial-failure retry.
            # If _dispatch_day3_offer fails mid-batch and the heartbeat re-fires,
            # contacts who already received the offer are silently skipped.
            from datetime import timezone as _tz
            cutoff = datetime.now(_tz.utc) - timedelta(hours=12)
            already_sent = (
                db.query(Message)
                .filter(
                    Message.contact_id == enr.contact_id,
                    Message.template_key == effective_template,
                    Message.created_at >= cutoff,
                )
                .first()
            )
            if already_sent:
                logger.debug("dedup: offer already sent to %s — skipping", enr.contact_id)
                continue

            variables: dict[str, str] = {
                "1": name,
                "2": (edition.payment_url if edition else None) or settings.program_payment_url or "",
            }

            result = provider.send_template(phone, effective_template, variables)

            db.add(Message(
                id=f"msg_{uuid4().hex[:8]}",
                contact_id=enr.contact_id,
                template_key=effective_template,
                variables=variables,
                provider_message_id=result.get("provider_message_id"),
                status=result.get("status", "queued"),
                provider=result.get("provider", "mock"),
            ))
            if result.get("status", "queued") != "failed":
                count += 1

        db.commit()
        return count

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="campaigns.dispatch_h_plus_2", bind=True, max_retries=3)
def dispatch_h_plus_2(
    self,
    campaign_key: str,
    cohort: str,
    day_number: int,
    edition_key: str = "",
    streamyard_url: str = "",
):
    """H+2 Day-3 Celery task — sends live_day3_offer_hplus2 to StreamYard-registered contacts.

    Scheduled only for Day 3; calls for other days are silently ignored.
    """
    if day_number != 3:
        logger.warning(
            "dispatch_h_plus_2 called for day_number=%d (expected 3) — skipping",
            day_number,
        )
        return {"dispatched": 0, "template_key": "live_day3_offer_hplus2"}

    logger.info(
        "Dispatching h_plus_2 for campaign=%s cohort=%s edition=%s",
        campaign_key, cohort, edition_key,
    )
    try:
        count = _dispatch_day3_offer(
            campaign_key=campaign_key,
            cohort=cohort,
            edition_key=edition_key,
        )
        logger.info("Dispatched %d messages (live_day3_offer_hplus2)", count)
        return {"dispatched": count, "template_key": "live_day3_offer_hplus2"}
    except Exception as exc:
        logger.error("Task dispatch_h_plus_2 failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _dispatch_day3_offer_hplus3(campaign_key: str, cohort: str, edition_key: str) -> int:
    """Send live_day3_offer_hplus3 (H+3 follow-up offer) to Day-3 StreamYard contacts.

    Second offer message, sent 1 hour after the H+2 first offer.
    Same audience filter as _dispatch_day3_offer (day2 or day3 StreamYard registered).
    Uses template live_day3_offer_hplus3 (or _utility variant for US/CA).
    """
    from shared.config.settings import settings

    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()
    try:
        provider = _get_provider()

        query = db.query(CampaignEnrollment).filter(
            CampaignEnrollment.campaign_key == campaign_key,
            CampaignEnrollment.cohort == cohort,
        )
        if edition_key:
            query = query.filter(CampaignEnrollment.edition_key == edition_key)
        enrollments = query.all()

        _BASE_TEMPLATE = "live_day3_offer_hplus3_v4"
        edition = None
        if edition_key:
            edition = (
                db.query(ChallengeEdition)
                .filter(ChallengeEdition.edition_key == edition_key)
                .first()
            )

        count = 0
        for enr in enrollments:
            consent = (
                db.query(Consent)
                .filter(Consent.contact_id == enr.contact_id, Consent.status == "opted_in")
                .first()
            )
            if not consent:
                continue
            if _contact_has_paid_offer(enr.contact_id, db):
                continue
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
                continue

            contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
            phone = contact.phone if contact else enr.contact_id
            first_name = (contact.first_name or "").strip() if contact else ""
            name = first_name or "vous"

            effective_template = resolve_template_key(_BASE_TEMPLATE, phone)

            from datetime import timezone as _tz
            cutoff = datetime.now(_tz.utc) - timedelta(hours=12)
            already_sent = (
                db.query(Message)
                .filter(
                    Message.contact_id == enr.contact_id,
                    Message.template_key == effective_template,
                    Message.created_at >= cutoff,
                )
                .first()
            )
            if already_sent:
                continue

            variables: dict[str, str] = {
                "1": name,
                "2": (edition.payment_url if edition else None) or settings.program_payment_url or "",
            }
            result = provider.send_template(phone, effective_template, variables)
            db.add(Message(
                id=f"msg_{uuid4().hex[:8]}",
                contact_id=enr.contact_id,
                template_key=effective_template,
                variables=variables,
                provider_message_id=result.get("provider_message_id"),
                status=result.get("status", "queued"),
                provider=result.get("provider", "mock"),
            ))
            if result.get("status", "queued") != "failed":
                count += 1

        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Worker startup: catch-up missed broadcasts ───────────────────────────────

from celery.signals import worker_ready  # noqa: E402


@worker_ready.connect
def _on_worker_ready(sender, **kwargs):
    """When the Celery worker starts, immediately check for missed broadcasts.

    This handles the common case where a container redeploy happens during or
    shortly after the broadcast window.  The catch-up window is 12 h — the
    same value used inside dispatch_daily_broadcasts.

    We dispatch as a task (not inline) so it goes through the normal
    retry / error-handling path.
    """
    logger.info("Worker ready — scheduling startup catch-up broadcast check")
    dispatch_daily_broadcasts.apply_async(countdown=5)


# ── Timed reminder offsets (replaces broken apply_async ETA mechanism) ─────────
# dispatch_daily_broadcasts runs every 10 min and checks these offsets.
# H-2 is excluded intentionally: it uses the same templates as the broadcast
# and would create duplicate messages. Only H-10, H+5, H+2-offer, H+3-offer kept.
_TIMED_REMINDER_OFFSETS: list[tuple[str, timedelta, str]] = [
    ("h10",       timedelta(minutes=-10), "h10"),
    ("h_plus_5",  timedelta(minutes=5),   "h_plus_5"),
    ("h_plus_2",  timedelta(hours=2),     "h_plus_2"),   # Day 3 offer — first send
    ("h_plus_3",  timedelta(hours=3),     "h_plus_3"),   # Day 3 offer — second send (H+3)
]
# ±9 min window (vs 10-min heartbeat period).
# Wider than ±5 min to tolerate Celery worker pickup delays — if the worker
# takes up to 9 min to process the heartbeat task, the reminder still fires.
# Double-fire is prevented by the AuditEvent idempotency check above.
_TIMED_REMINDER_WINDOW = timedelta(minutes=9)


def _dispatch_timed_reminders(edition: "ChallengeEdition", now_utc: datetime, db) -> list[dict]:
    """Check and fire timed reminders (H-10, H+5, H+2) for an active edition.

    Replaces the broken apply_async(eta=...) mechanism. Called every 10 min
    by dispatch_daily_broadcasts. Uses AuditEvent for idempotency.
    """
    cohort_config = get_cohort_config(edition.cohort)
    tz = ZoneInfo(cohort_config["timezone"])
    live_time_str = cohort_config["live_time"]
    live_hour, live_minute = (int(x) for x in live_time_str.split(":"))
    start_date = date.fromisoformat(edition.edition_date)
    fired: list[dict] = []

    for day_number in [1, 2, 3]:
        live_date = start_date + timedelta(days=day_number - 1)
        live_dt_local = datetime(live_date.year, live_date.month, live_date.day,
                                 live_hour, live_minute, tzinfo=tz)
        live_dt_utc = live_dt_local.astimezone(timezone.utc)

        for timing_key, offset, dispatch_timing in _TIMED_REMINDER_OFFSETS:
            # H+2 offer only on Day 3
            if timing_key == "h_plus_2" and day_number != 3:
                continue

            target_utc = live_dt_utc + offset
            if abs((now_utc - target_utc).total_seconds()) > _TIMED_REMINDER_WINDOW.total_seconds():
                continue  # not in fire window

            # Idempotency: skip if already dispatched
            audit_id = f"{edition.edition_key}:day{day_number}:{timing_key}"
            already = (
                db.query(AuditEvent)
                .filter(AuditEvent.name == "timed_reminder", AuditEvent.aggregate_id == audit_id)
                .first()
            )
            if already:
                continue

            logger.info("Firing timed reminder %s day=%d edition=%s", timing_key, day_number, edition.edition_key)
            try:
                if timing_key == "h_plus_2":
                    # H+2 offer: first send to StreamYard-registered contacts.
                    count = _dispatch_day3_offer(
                        campaign_key=edition.campaign_key,
                        cohort=edition.cohort,
                        edition_key=edition.edition_key,
                    )
                elif timing_key == "h_plus_3":
                    # H+3 offer: second send (follow-up) to StreamYard-registered contacts.
                    count = _dispatch_day3_offer_hplus3(
                        campaign_key=edition.campaign_key,
                        cohort=edition.cohort,
                        edition_key=edition.edition_key,
                    )
                else:
                    count = _dispatch_messages_for_cohort(
                        campaign_key=edition.campaign_key,
                        cohort=edition.cohort,
                        day_number=day_number,
                        edition_key=edition.edition_key,
                        timing=dispatch_timing,
                        streamyard_url="",
                    )
                db.add(AuditEvent(
                    name="timed_reminder",
                    aggregate_id=audit_id,
                    payload={"dispatched": count, "timing": timing_key, "day": day_number},
                ))
                db.commit()
                fired.append({"timing": timing_key, "day": day_number, "dispatched": count})
            except Exception as exc:
                logger.error("Failed timed reminder %s day%d: %s", timing_key, day_number, exc)

    return fired


@celery_app.task(name="campaigns.dispatch_daily_broadcasts", bind=True, max_retries=3)
def dispatch_daily_broadcasts(self, now_iso: str | None = None):
    """Send one campaign journey step per active edition, once per local day.
    Also fires timed reminders (H-10, H+5, H+2) based on clock proximity.

    The database remains the source of truth:
      - ChallengeEdition defines which editions are active.
      - CampaignEnrollment.current_step defines what each contact receives next.
      - AuditEvent prevents duplicate sends for the same edition/day.
    """
    from services.campaigns.app.main import broadcast_campaign_impl

    now_utc = (
        datetime.fromisoformat(now_iso).astimezone(timezone.utc)
        if now_iso
        else datetime.now(timezone.utc)
    )
    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()
    try:
        editions = db.query(ChallengeEdition).all()
        processed: list[dict] = []

        for edition in editions:
            cohort_config = get_cohort_config(edition.cohort)
            tz = ZoneInfo(cohort_config["timezone"])
            local_now = now_utc.astimezone(tz)
            local_today = local_now.date()
            broadcast_time = _parse_clock(cohort_config.get("broadcast_time", "09:00"))

            # ── Candidate dates: today + catch-up for missed broadcasts ──────────
            # If the beat restarts after midnight local time (e.g. container
            # redeploy at 23:50 Paris after a 19:00 broadcast was missed), the
            # normal check (local_now.time() >= broadcast_time) would skip today
            # because 00:00 < 19:00. The catch-up window looks back up to 12 h to
            # fire any broadcast that was scheduled but never recorded.
            _CATCHUP_HOURS = 12
            candidate_dates = []
            # Today: only if we are past the broadcast time
            if local_now.time() >= broadcast_time:
                candidate_dates.append(local_today)
            # Previous local day: fire if within catch-up window
            from datetime import timedelta as _td, date as _date
            local_yesterday = local_today - _td(days=1)
            scheduled_yesterday_utc = datetime(
                local_yesterday.year, local_yesterday.month, local_yesterday.day,
                broadcast_time.hour, broadcast_time.minute,
                tzinfo=tz,
            ).astimezone(timezone.utc)
            elapsed_h = (now_utc - scheduled_yesterday_utc).total_seconds() / 3600
            if 0 < elapsed_h <= _CATCHUP_HOURS:
                candidate_dates.append(local_yesterday)

            for local_date in candidate_dates:
                if not _edition_is_in_daily_window(edition.edition_date, local_date):
                    continue

                # ── Atomic lock: INSERT the audit slot BEFORE sending ─────────
                # If another worker (or a manual call) is already handling this
                # edition+date, _try_claim_broadcast_slot returns False and we
                # skip — no double-send possible.
                if not _try_claim_broadcast_slot(db, edition, local_date):
                    logger.info(
                        "Broadcast slot already claimed for %s on %s — skipping",
                        edition.edition_key, local_date,
                    )
                    continue

                catchup = local_date < local_today
                if catchup:
                    logger.warning(
                        "Catch-up broadcast for %s on %s (beat was down during window)",
                        edition.edition_key, local_date,
                    )
                result = broadcast_campaign_impl(
                    db,
                    campaign_key=edition.campaign_key,
                    cohort=edition.cohort,
                    edition_key=edition.edition_key,
                    scheduled_local_date=local_date,
                )
                # Update the audit record with final send counts
                _update_broadcast_audit(db, edition, local_date, result)
                processed.append({
                    "edition_key": edition.edition_key,
                    "cohort": edition.cohort,
                    "local_date": local_date.isoformat(),
                    "queued": result["queued"],
                    "catchup": catchup,
                })

        # ── Timed reminders (H-10, H+5, H+2) for all active editions ──────
        reminders_fired: list[dict] = []
        for edition in editions:
            if _edition_is_in_daily_window(edition.edition_date, datetime.now(timezone.utc).date()):
                reminders_fired.extend(_dispatch_timed_reminders(edition, now_utc, db))

        return {"processed": len(processed), "editions": processed, "reminders": reminders_fired}
    except Exception as exc:
        logger.error("Task dispatch_daily_broadcasts failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
