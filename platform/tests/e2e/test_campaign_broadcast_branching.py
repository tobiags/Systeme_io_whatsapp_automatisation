"""Tests for 3-way behavioral branching in campaign broadcast.

Spec v2: Each live day has 3 possible templates based on the contact's StreamYard state
for the PRIOR day:

  (a) day{N}_live_joined event exists       → main (attended) template
      e.g. live_day2_attended
  (b) day{N}_streamyard_registered only     → registered_absent template
      e.g. live_day2_registered_absent
  (c) neither event                         → no_show template
      e.g. live_day2_not_registered

Same 3-way logic applies for DAY_3 (based on day2 state) and AFTER_1 (based on day3 state).
"""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.scoring.app.main import app as scoring_app

campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)
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


def _broadcast() -> list[dict]:
    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    return resp.json()["messages"]


# ── DAY_2 branching (3 branches) ─────────────────────────────────────────────

def test_day2_attended_gets_attended_template():
    """Contact who attended Day 1 live → live_day2_attended."""
    _enroll_at_step("ct_v2_day2_attended", "DAY_2")
    _grant_consent("ct_v2_day2_attended")
    _record_event("ct_v2_day2_attended", "day1_live_joined")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day2_attended")
    assert msg["template_key"] == "live_day2_attended"


def test_day2_registered_absent_gets_registered_absent_template():
    """Contact who registered on StreamYard but didn't attend → live_day2_registered_absent."""
    _enroll_at_step("ct_v2_day2_reg_absent", "DAY_2")
    _grant_consent("ct_v2_day2_reg_absent")
    _record_event("ct_v2_day2_reg_absent", "day1_streamyard_registered")
    # No day1_live_joined event

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day2_reg_absent")
    assert msg["template_key"] == "live_day2_registered_absent"


def test_day2_not_registered_gets_no_show_template():
    """Contact with no StreamYard interaction at all → live_day2_not_registered."""
    _enroll_at_step("ct_v2_day2_noshow", "DAY_2")
    _grant_consent("ct_v2_day2_noshow")
    # No events at all

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day2_noshow")
    assert msg["template_key"] == "live_day2_not_registered"


def test_day2_three_contacts_route_correctly():
    """Three contacts in same cohort each receive a different template."""
    _enroll_at_step("ct_v2_mix_attended", "DAY_2")
    _enroll_at_step("ct_v2_mix_reg_abs", "DAY_2")
    _enroll_at_step("ct_v2_mix_noshow", "DAY_2")
    _grant_consent("ct_v2_mix_attended")
    _grant_consent("ct_v2_mix_reg_abs")
    _grant_consent("ct_v2_mix_noshow")
    _record_event("ct_v2_mix_attended", "day1_live_joined")
    _record_event("ct_v2_mix_reg_abs", "day1_streamyard_registered")
    # ct_v2_mix_noshow: no events

    messages = _broadcast()
    by_contact = {m["contact_id"]: m["template_key"] for m in messages}
    assert by_contact["ct_v2_mix_attended"] == "live_day2_attended"
    assert by_contact["ct_v2_mix_reg_abs"] == "live_day2_registered_absent"
    assert by_contact["ct_v2_mix_noshow"] == "live_day2_not_registered"


# ── DAY_3 branching (3 branches) ─────────────────────────────────────────────

def test_day3_attended_gets_attended_template():
    """Contact who attended Day 2 live → live_day3_attended."""
    _enroll_at_step("ct_v2_day3_attended", "DAY_3")
    _grant_consent("ct_v2_day3_attended")
    _record_event("ct_v2_day3_attended", "day2_live_joined")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day3_attended")
    assert msg["template_key"] == "live_day3_attended"


def test_day3_registered_absent_gets_registered_absent_template():
    """Contact registered on StreamYard for Day 2 but absent → live_day3_registered_absent."""
    _enroll_at_step("ct_v2_day3_reg_absent", "DAY_3")
    _grant_consent("ct_v2_day3_reg_absent")
    _record_event("ct_v2_day3_reg_absent", "day2_streamyard_registered")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day3_reg_absent")
    assert msg["template_key"] == "live_day3_registered_absent"


def test_day3_no_show_gets_no_show_template():
    """Contact with no Day 2 interaction → live_day3_not_registered."""
    _enroll_at_step("ct_v2_day3_noshow", "DAY_3")
    _grant_consent("ct_v2_day3_noshow")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day3_noshow")
    assert msg["template_key"] == "live_day3_not_registered"


# ── AFTER_1 branching (3 branches) ───────────────────────────────────────────

def test_after1_attended_gets_recap_attended():
    """Contact who attended Day 3 → post_recap_attended."""
    _enroll_at_step("ct_v2_after1_attended", "AFTER_1")
    _grant_consent("ct_v2_after1_attended")
    _record_event("ct_v2_after1_attended", "day3_live_joined")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_after1_attended")
    assert msg["template_key"] == "post_recap_attended"


def test_after1_registered_absent_gets_registered_absent():
    """Contact registered on StreamYard for Day 3 but absent → post_recap_registered_absent."""
    _enroll_at_step("ct_v2_after1_reg_abs", "AFTER_1")
    _grant_consent("ct_v2_after1_reg_abs")
    _record_event("ct_v2_after1_reg_abs", "day3_streamyard_registered")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_after1_reg_abs")
    assert msg["template_key"] == "post_recap_registered_absent"


def test_after1_no_show_gets_not_registered():
    """Contact with no Day 3 interaction → post_recap_not_registered."""
    _enroll_at_step("ct_v2_after1_noshow", "AFTER_1")
    _grant_consent("ct_v2_after1_noshow")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_after1_noshow")
    assert msg["template_key"] == "post_recap_not_registered"


# ── Non-branching steps are unaffected ───────────────────────────────────────

def test_day1_no_branching():
    """DAY_1 step always uses live_day1 regardless of score events."""
    _enroll_at_step("ct_v2_day1_nobranch", "DAY_1")
    _grant_consent("ct_v2_day1_nobranch")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_day1_nobranch")
    assert msg["template_key"] == "live_day1"


def test_welcome_no_branching():
    """WELCOME step always uses 'welcome' regardless of score events."""
    _enroll_at_step("ct_v2_welcome_nobranch", "WELCOME")
    _grant_consent("ct_v2_welcome_nobranch")

    messages = _broadcast()
    msg = next(m for m in messages if m["contact_id"] == "ct_v2_welcome_nobranch")
    assert msg["template_key"] == "welcome"
