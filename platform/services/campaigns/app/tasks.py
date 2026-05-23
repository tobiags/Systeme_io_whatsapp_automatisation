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
_TEMPLATE_MAP: dict[str, str] = {
    "h2":        "h2",
    "h10":       "h10",
    "h_plus_5":  "hplus5",
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


def _broadcast_already_recorded(db, edition_key: str, local_today: date) -> bool:
    aggregate_id = f"{edition_key}:{local_today.isoformat()}"
    return (
        db.query(AuditEvent)
        .filter(
            AuditEvent.name == "campaign_daily_broadcast",
            AuditEvent.aggregate_id == aggregate_id,
        )
        .first()
        is not None
    )


def _record_broadcast_audit(db, edition: ChallengeEdition, local_today: date, payload: dict) -> None:
    db.add(AuditEvent(
        name="campaign_daily_broadcast",
        aggregate_id=f"{edition.edition_key}:{local_today.isoformat()}",
        payload={
            "campaign_key": edition.campaign_key,
            "cohort": edition.cohort,
            "edition_key": edition.edition_key,
            "local_date": local_today.isoformat(),
            **payload,
        },
    ))
    db.commit()


def _resolve_timed_template_key(day_number: int, timing: str, contact_id: str, db) -> str:
    """Resolve the timed reminder template for a contact.

    Day 1 uses generic reminder keys for every timing.
    Day 2 / Day 3 use behavioral branching for the H-2 reminder only, based on
    the prior day's StreamYard events. H-10 and H+5 remain generic day-level
    reminders because the validated template set only defines:
      - live_day{N}_h10
      - live_day{N}_hplus5
    """
    suffix = _TEMPLATE_MAP[timing]
    if timing != "h2" or day_number == 1:
        return f"live_day{day_number}_{suffix}"

    if day_number == 2:
        attended_event = "day1_live_joined"
        registered_event = "day1_streamyard_registered"
        attended_template = "live_day2_attended_v2"
        registered_absent_template = "live_day2_registered_absent"
        no_show_template = "live_day2_not_registered"
    elif day_number == 3:
        attended_event = "day2_live_joined"
        registered_event = "day2_streamyard_registered"
        attended_template = "live_day3_attended_v2"
        registered_absent_template = "live_day3_registered_absent"
        no_show_template = "live_day3_not_registered"
    else:
        return f"live_day{day_number}_{suffix}"

    attended = (
        db.query(ScoreEvent)
        .filter(
            ScoreEvent.contact_id == contact_id,
            ScoreEvent.event_type == attended_event,
        )
        .first()
    )
    if attended:
        return attended_template

    registered = (
        db.query(ScoreEvent)
        .filter(
            ScoreEvent.contact_id == contact_id,
            ScoreEvent.event_type == registered_event,
        )
        .first()
    )
    if registered:
        return registered_absent_template
    return no_show_template


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

            variables = _build_task_variables(
                first_name=first_name,
                timing=timing,
                streamyard_url=streamyard_url,
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

        template_key = "live_day3_offer_hplus2"
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

            # Filter: only day3_streamyard_registered contacts
            registered = (
                db.query(ScoreEvent)
                .filter(
                    ScoreEvent.contact_id == enr.contact_id,
                    ScoreEvent.event_type == "day3_streamyard_registered",
                )
                .first()
            )
            if not registered:
                continue

            contact = db.query(Contact).filter(Contact.id == enr.contact_id).first()
            phone = contact.phone if contact else enr.contact_id
            first_name = (contact.first_name or "").strip() if contact else ""
            name = first_name or "vous"

            variables: dict[str, str] = {
                "1": name,
                "2": (edition.payment_url if edition else None) or settings.program_payment_url or "",
            }

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


@celery_app.task(name="campaigns.dispatch_daily_broadcasts", bind=True, max_retries=3)
def dispatch_daily_broadcasts(self, now_iso: str | None = None):
    """Send one campaign journey step per active edition, once per local day.

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

            if local_now.time() < broadcast_time:
                continue
            if not _edition_is_in_daily_window(edition.edition_date, local_today):
                continue
            if _broadcast_already_recorded(db, edition.edition_key, local_today):
                continue

            result = broadcast_campaign_impl(
                db,
                campaign_key=edition.campaign_key,
                cohort=edition.cohort,
                edition_key=edition.edition_key,
            )
            _record_broadcast_audit(db, edition, local_today, result)
            processed.append({
                "edition_key": edition.edition_key,
                "cohort": edition.cohort,
                "local_date": local_today.isoformat(),
                "queued": result["queued"],
            })

        return {"processed": len(processed), "editions": processed}
    except Exception as exc:
        logger.error("Task dispatch_daily_broadcasts failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
