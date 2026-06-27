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
# Generated pattern: f"live_day{N}_{suffix}" → e.g. live_day1_h10_v5
_TEMPLATE_MAP: dict[str, str] = {
    "h10": "h10_v5",   # → live_day{N}_h10_v5
}

# Timings that include the StreamYard live link ({{2}}) + live time ({{3}})
_TIMINGS_WITH_URL = {"h10"}


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


from services.campaigns.app.utils import broadcast_already_recorded, broadcast_audit_id, broadcast_lock, redis_lock, resolve_template_key


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


def _record_broadcast_audit(db, edition: ChallengeEdition, local_today: date, payload: dict) -> None:
    """Record broadcast completion as an AuditEvent.

    Uses INSERT … ON CONFLICT DO NOTHING so a duplicate call is harmless
    (the UNIQUE constraint on aggregate_id protects against double-inserts).
    This is called AFTER broadcast_campaign_impl succeeds — never before —
    so there's no risk of a "pending" slot blocking future attempts.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    aggregate_id = f"{edition.edition_key}:{local_today.isoformat()}"
    stmt = pg_insert(AuditEvent).values(
        name="campaign_daily_broadcast",
        aggregate_id=aggregate_id,
        payload={
            "campaign_key": edition.campaign_key,
            "cohort": edition.cohort,
            "edition_key": edition.edition_key,
            "local_date": local_today.isoformat(),
            **payload,
        },
    ).on_conflict_do_nothing(index_elements=["aggregate_id"])
    db.execute(stmt)
    db.commit()


def _resolve_timed_template_key(day_number: int, timing: str, contact_id: str, db) -> str:
    """Resolve the H-10 timed reminder template for a contact (no branching)."""
    suffix = _TEMPLATE_MAP[timing]
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
            # Latest consent record wins — STOP after opt-in must block
            consent = (
                db.query(Consent)
                .filter(Consent.contact_id == enr.contact_id)
                .order_by(Consent.id.desc())
                .first()
            )
            if not consent or consent.status != "opted_in":
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
            db.commit()  # commit per-message: survives a mid-loop failure on retry
            if result.get("status", "queued") != "failed":
                count += 1

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

dispatch_h10 = _make_dispatch_task("h10")


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
        with broadcast_lock(edition_key, local_date) as acquired:
            if not acquired:
                logger.info("dispatch_broadcast lock held: edition=%s date=%s", edition_key, local_date_str)
                return {"queued": 0, "skipped_lock_held": True}

            if _broadcast_already_recorded(db, edition_key, local_date):
                logger.info(
                    "dispatch_broadcast skipped (already done): edition=%s date=%s",
                    edition_key, local_date_str,
                )
                return {"queued": 0, "skipped_already_broadcast": True}

            from services.campaigns.app.main import broadcast_campaign_impl
            result = broadcast_campaign_impl(
                db,
                campaign_key=campaign_key,
                cohort=cohort,
                edition_key=edition_key,
                scheduled_local_date=local_date,
            )

            edition = db.query(ChallengeEdition).filter(
                ChallengeEdition.edition_key == edition_key
            ).first()
            if edition:
                _record_broadcast_audit(db, edition, local_date, result)

            logger.info(
                "dispatch_broadcast complete: edition=%s date=%s queued=%d",
                edition_key, local_date_str, result.get("queued", 0),
            )
            return result
    except Exception as exc:
        logger.error("dispatch_broadcast failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


# ── Timed reminder offsets (replaces broken apply_async ETA mechanism) ─────────
# dispatch_daily_broadcasts runs every 10 min and checks these offsets.
# Only H-10 is kept (H+5, H+2-offer, H+3-offer removed in v5 journey).
_TIMED_REMINDER_OFFSETS: list[tuple[str, timedelta, str]] = [
    ("h10", timedelta(minutes=-10), "h10"),
]
# ±14 min window: covers 1.5 heartbeat cycles so a failed H-10 at tick N
# can be retried at tick N+1 (10 min later) and still be within the window.
_TIMED_REMINDER_WINDOW = timedelta(minutes=14)


def _dispatch_timed_reminders(edition: "ChallengeEdition", now_utc: datetime, db) -> list[dict]:
    """Check and fire H-10 reminders for an active edition.

    Called every 10 min by dispatch_daily_broadcasts. Uses AuditEvent for idempotency.
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
            target_utc = live_dt_utc + offset
            if abs((now_utc - target_utc).total_seconds()) > _TIMED_REMINDER_WINDOW.total_seconds():
                continue  # not in fire window

            audit_id = f"{edition.edition_key}:day{day_number}:{timing_key}"
            lock_key = f"timed_reminder:{audit_id}"
            with redis_lock(lock_key, timeout=600) as acquired:
                if not acquired:
                    logger.info("Timed reminder lock held: %s", audit_id)
                    continue

                already = (
                    db.query(AuditEvent)
                    .filter(AuditEvent.name == "timed_reminder", AuditEvent.aggregate_id == audit_id)
                    .first()
                )
                if already:
                    continue

                logger.info("Firing timed reminder %s day=%d edition=%s", timing_key, day_number, edition.edition_key)
                try:
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
        cutoff = (now_utc.date() - timedelta(days=7)).isoformat()
        editions = db.query(ChallengeEdition).filter(
            ChallengeEdition.edition_date >= cutoff
        ).all()
        processed: list[dict] = []

        for edition in editions:
            cohort_config = get_cohort_config(edition.cohort)
            tz = ZoneInfo(cohort_config["timezone"])
            local_now = now_utc.astimezone(tz)
            local_today = local_now.date()
            broadcast_time = _parse_clock(cohort_config.get("broadcast_time", "09:00"))

            # ── Gate: only fire after the broadcast time in the local timezone ──
            if local_now.time() < broadcast_time:
                continue

            for local_date in [local_today]:
                if not _edition_is_in_daily_window(edition.edition_date, local_date):
                    continue

                with broadcast_lock(edition.edition_key, local_date) as acquired:
                    if not acquired:
                        logger.info("Broadcast lock held by another process: %s %s", edition.edition_key, local_date)
                        continue

                    if _broadcast_already_recorded(db, edition.edition_key, local_date):
                        continue

                    result = broadcast_campaign_impl(
                        db,
                        campaign_key=edition.campaign_key,
                        cohort=edition.cohort,
                        edition_key=edition.edition_key,
                        scheduled_local_date=local_date,
                    )

                    _record_broadcast_audit(db, edition, local_date, result)

                    processed.append({
                        "edition_key": edition.edition_key,
                        "cohort": edition.cohort,
                        "local_date": local_date.isoformat(),
                        "queued": result["queued"],
                    })

        # ── Timed reminders (H-10, H+5, H+2) for all active editions ──────
        reminders_fired: list[dict] = []
        for edition in editions:
            if _edition_is_in_daily_window(edition.edition_date, now_utc.date()):
                reminders_fired.extend(_dispatch_timed_reminders(edition, now_utc, db))

        return {"processed": len(processed), "editions": processed, "reminders": reminders_fired}
    except Exception as exc:
        logger.error("Task dispatch_daily_broadcasts failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
