"""Celery tasks for timed live-session message dispatch.

Each live day (Day 1, Day 2, Day 3) triggers 4 tasks:
  • H-6h   — morning motivation / day brief           → day{N}_prelive_h6
  • H-45m  — "live starts soon" + StreamYard link     → day{N}_prelive_h45
  • H-10m  — final countdown reminder                 → day{N}_prelive_h10
  • H+30m  — post-live recap / replay link            → day{N}_postlive_recap

Each task:
  1. Resolves enrolled contacts for the given campaign/cohort/edition.
  2. Looks up Contact (first_name + phone) for each enrollment.
  3. Builds template variables: {{1}} first_name, {{2}} StreamYard URL (h45 only),
     {{3}} session time.
  4. Calls WatiProvider (real API) or MockProvider (dev/test, no credentials).
  5. Persists a Message audit row with the actual provider status.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from services.campaigns.app.celery_app import celery_app
from services.campaigns.app.challenge_calendar import get_cohort_config
from shared.db.models import CampaignEnrollment, Contact, Message
from shared.db.session import get_engine_and_session

logger = logging.getLogger(__name__)

# Template key pattern: day{N}_{timing}
_TEMPLATE_MAP: dict[str, str] = {
    "h6":     "prelive_h6",
    "h45":    "prelive_h45",
    "h10":    "prelive_h10",
    "recap":  "postlive_recap",
}

# Template timings that include the StreamYard live link ({{2}})
_TIMINGS_WITH_URL = {"h45"}


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
    {{2}} — StreamYard URL (h45 only — 45 min before live)
    {{3}} — live session time, e.g. "21:00" (h45 + h10)
    """
    name = (first_name or "").strip() or "vous"
    variables: dict[str, str] = {"1": name}

    if timing in _TIMINGS_WITH_URL:
        cohort_cfg = get_cohort_config(cohort)
        variables["2"] = streamyard_url or ""
        variables["3"] = cohort_cfg.get("live_time", "21:00")

    return variables


def _dispatch_messages_for_cohort(
    campaign_key: str,
    cohort: str,
    template_key: str,
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
        suffix = _TEMPLATE_MAP[timing]
        template_key = f"day{day_number}_{suffix}"
        logger.info(
            "Dispatching %s for campaign=%s cohort=%s day=%d edition=%s url=%s",
            timing, campaign_key, cohort, day_number, edition_key,
            "set" if streamyard_url else "empty",
        )
        try:
            count = _dispatch_messages_for_cohort(
                campaign_key=campaign_key,
                cohort=cohort,
                template_key=template_key,
                edition_key=edition_key,
                timing=timing,
                streamyard_url=streamyard_url,
            )
            logger.info("Dispatched %d messages (%s)", count, template_key)
            return {"dispatched": count, "template_key": template_key}
        except Exception as exc:
            logger.error("Task %s failed: %s", self.name, exc)
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    return _task


# ── Exported tasks ────────────────────────────────────────────────────────────

dispatch_h6    = _make_dispatch_task("h6")
dispatch_h45   = _make_dispatch_task("h45")
dispatch_h10   = _make_dispatch_task("h10")
dispatch_recap = _make_dispatch_task("recap")
