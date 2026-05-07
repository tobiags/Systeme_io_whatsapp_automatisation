"""Celery tasks for timed live-session message dispatch.

Each live day (Day 1, Day 2, Day 3) triggers 4 tasks:
  • H-6h   — morning motivation / day brief
  • H-45m  — "live starts soon" + StreamYard link
  • H-10m  — final countdown reminder
  • H+0    — post-live replay / recap link (sent ~30 min after live starts)

Tasks queue messages via the same DB + Message model used by the rest of the
platform. In production the Wati provider picks up queued messages; in tests
the mock provider is used.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from services.campaigns.app.celery_app import celery_app
from shared.db.models import CampaignEnrollment, Message
from shared.db.session import get_engine_and_session

logger = logging.getLogger(__name__)

# Template key pattern: <step>_<timing>
#   e.g. "day1_prelive_h6", "day2_prelive_h45", "day3_postlive_recap"
_TEMPLATE_MAP: dict[str, str] = {
    "h6":     "prelive_h6",
    "h45":    "prelive_h45",
    "h10":    "prelive_h10",
    "recap":  "postlive_recap",
}


def _queue_messages_for_cohort(
    campaign_key: str,
    cohort: str,
    template_key: str,
    edition_key: str,
) -> int:
    """Create queued Message rows for every enrolled contact in the cohort.

    Returns the number of messages queued.
    """
    _, SessionLocal = get_engine_and_session()
    db = SessionLocal()
    try:
        enrollments = (
            db.query(CampaignEnrollment)
            .filter(
                CampaignEnrollment.campaign_key == campaign_key,
                CampaignEnrollment.cohort == cohort,
                # Only target enrollments for this specific edition when provided.
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
            db.add(Message(
                id=f"msg_{uuid4().hex[:8]}",
                contact_id=enr.contact_id,
                template_key=template_key,
                variables={},
                status="queued",
                provider="mock",
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
            "Dispatching %s for campaign=%s cohort=%s day=%d edition=%s",
            timing, campaign_key, cohort, day_number, edition_key,
        )
        try:
            count = _queue_messages_for_cohort(
                campaign_key=campaign_key,
                cohort=cohort,
                template_key=template_key,
                edition_key=edition_key,
            )
            logger.info("Queued %d messages (%s)", count, template_key)
            return {"queued": count, "template_key": template_key}
        except Exception as exc:
            logger.error("Task %s failed: %s", self.name, exc)
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    return _task


# ── Exported tasks ────────────────────────────────────────────────────────────

dispatch_h6    = _make_dispatch_task("h6")
dispatch_h45   = _make_dispatch_task("h45")
dispatch_h10   = _make_dispatch_task("h10")
dispatch_recap = _make_dispatch_task("recap")
