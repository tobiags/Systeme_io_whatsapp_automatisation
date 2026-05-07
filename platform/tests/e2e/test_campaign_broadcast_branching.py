"""Tests for behavioral branching in campaign broadcast.

Spec: Jour 2 message differs based on whether the contact attended Jour 1.
  - Attended  (day1_live_joined event exists) → challenge_day_2
  - Absent    (no event)                       → challenge_day_2_catchup
Same logic applies for Jour 3 based on day2_live_joined.
"""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.scoring.app.main import app as scoring_app

campaigns_client = TestClient(campaigns_app)
scoring_client = TestClient(scoring_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"


def _enroll_at_step(contact_id: str, step: str) -> None:
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
        "current_step": step,
    })
    assert resp.status_code == 201


def _record_event(contact_id: str, event_type: str) -> None:
    resp = scoring_client.post("/scores/events", json={
        "contact_id": contact_id,
        "event_type": event_type,
    })
    assert resp.status_code == 201


def _broadcast() -> list[dict]:
    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    return resp.json()["messages"]


# ── DAY_2 branching ───────────────────────────────────────────────────────────

def test_day2_present_gets_continuity_template():
    """Contact who attended Day 1 receives challenge_day_2."""
    _enroll_at_step("ct_day2_present", "DAY_2")
    _record_event("ct_day2_present", "day1_live_joined")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_day2_present")
    assert msg["template_key"] == "challenge_day_2"


def test_day2_absent_gets_catchup_template():
    """Contact who missed Day 1 receives challenge_day_2_catchup."""
    _enroll_at_step("ct_day2_absent", "DAY_2")
    # No day1_live_joined event recorded

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_day2_absent")
    assert msg["template_key"] == "challenge_day_2_catchup"


def test_day2_mixed_cohort_routes_correctly():
    """Two contacts in same cohort receive different templates based on attendance."""
    _enroll_at_step("ct_day2_mix_present", "DAY_2")
    _enroll_at_step("ct_day2_mix_absent", "DAY_2")
    _record_event("ct_day2_mix_present", "day1_live_joined")

    messages = _broadcast()
    by_contact = {m["contact_id"]: m["template_key"] for m in messages}
    assert by_contact["ct_day2_mix_present"] == "challenge_day_2"
    assert by_contact["ct_day2_mix_absent"] == "challenge_day_2_catchup"


# ── DAY_3 branching ───────────────────────────────────────────────────────────

def test_day3_present_gets_continuity_template():
    """Contact who attended Day 2 receives challenge_day_3."""
    _enroll_at_step("ct_day3_present", "DAY_3")
    _record_event("ct_day3_present", "day2_live_joined")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_day3_present")
    assert msg["template_key"] == "challenge_day_3"


def test_day3_absent_gets_catchup_template():
    """Contact who missed Day 2 receives challenge_day_3_catchup."""
    _enroll_at_step("ct_day3_absent", "DAY_3")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_day3_absent")
    assert msg["template_key"] == "challenge_day_3_catchup"


# ── Non-branching steps are unaffected ───────────────────────────────────────

def test_day1_no_branching():
    """DAY_1 step always uses challenge_day_1 regardless of score events."""
    _enroll_at_step("ct_day1_nobranch", "DAY_1")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_day1_nobranch")
    assert msg["template_key"] == "challenge_day_1"
