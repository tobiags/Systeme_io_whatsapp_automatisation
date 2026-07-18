"""Tests for 3-way behavioral branching in campaign broadcast.

Spec (see services/campaigns/app/rules.py DEFAULT_JOURNEY): DAY_2 and DAY_3
each have 3 possible templates based on the contact's StreamYard state for
the PRIOR day:

  (a) day{N}_live_joined event exists       → main (attended) template
      e.g. live_day2_attended_v1
  (b) day{N}_streamyard_registered only     → registered_absent template
  (c) neither event                         → no_show template

AFTER_1 (and the other post-challenge steps) have no branching — they
always send their single configured template regardless of score events.

Every scheduled step (everything except WELCOME) is gated on the edition's
edition_date via `_step_is_due_on_local_date` — the broadcast is only sent
to a contact whose enrolled edition is "due" for the patched local date, so
each test here seeds a `ChallengeEdition` and patches `_local_broadcast_date`
to the day matching the step under test (see test_broadcast_step_progression.py
for the same pattern).
"""
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.scoring.app.main import app as scoring_app
from shared.db.models import ChallengeEdition
from tests.conftest import _TestingSession

campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)
scoring_client = TestClient(scoring_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"
EDITION_KEY = "2026-06-08-eu"
EDITION_DATE = "2026-06-08"  # Day 1
DAY_1_DATE = date(2026, 6, 8)
DAY_2_DATE = date(2026, 6, 9)
DAY_3_DATE = date(2026, 6, 10)
AFTER_1_DATE = date(2026, 6, 12)  # edition_date + 4


def _seed_edition(edition_key: str = EDITION_KEY, edition_date: str = EDITION_DATE) -> None:
    db = _TestingSession()
    try:
        db.add(ChallengeEdition(
            id=f"ed_{edition_key}",
            campaign_key=CAMPAIGN_KEY,
            edition_key=edition_key,
            cohort=COHORT,
            edition_date=edition_date,
        ))
        db.commit()
    finally:
        db.close()


def _enroll_at_step(contact_id: str, step: str) -> None:
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
        "edition_key": EDITION_KEY,
        "current_step": step,
    })
    assert resp.status_code == 201


def _grant_consent(contact_id: str) -> None:
    resp = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "test",
    })
    assert resp.status_code == 201


def _record_event(contact_id: str, event_type: str) -> None:
    resp = scoring_client.post("/scores/events", json={
        "contact_id": contact_id,
        "event_type": event_type,
    })
    assert resp.status_code == 201


def _broadcast(local_day: date) -> list[dict]:
    with patch("services.campaigns.app.main._local_broadcast_date", return_value=local_day):
        resp = campaigns_client.post("/campaigns/broadcast", json={
            "campaign_key": CAMPAIGN_KEY,
            "cohort": COHORT,
            "edition_key": EDITION_KEY,
        })
    assert resp.status_code == 200
    return resp.json()["messages"]


# ── DAY_2 branching (3 branches) ─────────────────────────────────────────────

def test_day2_attended_gets_attended_template():
    """Contact who attended Day 1 live → live_day2_attended_v1."""
    _seed_edition()
    _enroll_at_step("ct_v2_day2_attended", "DAY_2")
    _grant_consent("ct_v2_day2_attended")
    _record_event("ct_v2_day2_attended", "day1_live_joined")

    messages = _broadcast(DAY_2_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day2_attended")
    assert msg["template_key"] == "live_day2_attended_v1"


def test_day2_registered_absent_gets_registered_absent_template():
    """Contact who registered on StreamYard but didn't attend → live_day2_registered_absent_v1."""
    _seed_edition()
    _enroll_at_step("ct_v2_day2_reg_absent", "DAY_2")
    _grant_consent("ct_v2_day2_reg_absent")
    _record_event("ct_v2_day2_reg_absent", "day1_streamyard_registered")
    # No day1_live_joined event

    messages = _broadcast(DAY_2_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day2_reg_absent")
    assert msg["template_key"] == "live_day2_registered_absent_v1"


def test_day2_not_registered_gets_no_show_template():
    """Contact with no StreamYard interaction at all → live_day2_not_registered_v1."""
    _seed_edition()
    _enroll_at_step("ct_v2_day2_noshow", "DAY_2")
    _grant_consent("ct_v2_day2_noshow")
    # No events at all

    messages = _broadcast(DAY_2_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day2_noshow")
    assert msg["template_key"] == "live_day2_not_registered_v1"


def test_day2_three_contacts_route_correctly():
    """Three contacts in same cohort each receive a different template."""
    _seed_edition()
    _enroll_at_step("ct_v2_mix_attended", "DAY_2")
    _enroll_at_step("ct_v2_mix_reg_abs", "DAY_2")
    _enroll_at_step("ct_v2_mix_noshow", "DAY_2")
    _grant_consent("ct_v2_mix_attended")
    _grant_consent("ct_v2_mix_reg_abs")
    _grant_consent("ct_v2_mix_noshow")
    _record_event("ct_v2_mix_attended", "day1_live_joined")
    _record_event("ct_v2_mix_reg_abs", "day1_streamyard_registered")
    # ct_v2_mix_noshow: no events

    messages = _broadcast(DAY_2_DATE)
    by_contact = {m["contact_id"]: m["template_key"] for m in messages}
    assert by_contact["ct_v2_mix_attended"] == "live_day2_attended_v1"
    assert by_contact["ct_v2_mix_reg_abs"] == "live_day2_registered_absent_v1"
    assert by_contact["ct_v2_mix_noshow"] == "live_day2_not_registered_v1"


# ── DAY_3 branching (3 branches) ─────────────────────────────────────────────

def test_day3_attended_gets_attended_template():
    """Contact who attended Day 2 live → live_day3_attended_v1."""
    _seed_edition()
    _enroll_at_step("ct_v2_day3_attended", "DAY_3")
    _grant_consent("ct_v2_day3_attended")
    _record_event("ct_v2_day3_attended", "day2_live_joined")

    messages = _broadcast(DAY_3_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day3_attended")
    assert msg["template_key"] == "live_day3_attended_v1"


def test_day3_registered_absent_gets_registered_absent_template():
    """Contact registered on StreamYard for Day 2 but absent → live_day3_registered_absent_v1."""
    _seed_edition()
    _enroll_at_step("ct_v2_day3_reg_absent", "DAY_3")
    _grant_consent("ct_v2_day3_reg_absent")
    _record_event("ct_v2_day3_reg_absent", "day2_streamyard_registered")

    messages = _broadcast(DAY_3_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day3_reg_absent")
    assert msg["template_key"] == "live_day3_registered_absent_v1"


def test_day3_no_show_gets_no_show_template():
    """Contact with no Day 2 interaction → live_day3_not_registered_v1."""
    _seed_edition()
    _enroll_at_step("ct_v2_day3_noshow", "DAY_3")
    _grant_consent("ct_v2_day3_noshow")

    messages = _broadcast(DAY_3_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day3_noshow")
    assert msg["template_key"] == "live_day3_not_registered_v1"


# ── AFTER_1: no branching (rules.py has no registered_absent/no_show for it) ─

def test_after1_always_gets_testimonials_template():
    """AFTER_1 has no 3-way branching — always sends post_testimonials_v1
    regardless of the contact's Day 3 attendance state."""
    _seed_edition()
    _enroll_at_step("ct_v2_after1_any", "AFTER_1")
    _grant_consent("ct_v2_after1_any")
    _record_event("ct_v2_after1_any", "day3_live_joined")

    messages = _broadcast(AFTER_1_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_after1_any")
    assert msg["template_key"] == "post_testimonials_v1"


# ── Non-branching steps are unaffected ───────────────────────────────────────

def test_day1_no_branching():
    """DAY_1 step always uses live_day1_v1 regardless of score events."""
    _seed_edition()
    _enroll_at_step("ct_v2_day1_nobranch", "DAY_1")
    _grant_consent("ct_v2_day1_nobranch")

    messages = _broadcast(DAY_1_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day1_nobranch")
    assert msg["template_key"] == "live_day1_v1"


def test_welcome_no_branching():
    """WELCOME step always uses 'welcome_v1' regardless of score events."""
    _seed_edition()
    _enroll_at_step("ct_v2_welcome_nobranch", "WELCOME")
    _grant_consent("ct_v2_welcome_nobranch")

    messages = _broadcast(DAY_1_DATE)
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_welcome_nobranch")
    assert msg["template_key"] == "welcome_v1"
