"""Tests for journey step progression after broadcast.

After each broadcast, a contact's current_step must advance to the next step
in the DEFAULT_JOURNEY sequence so that the next broadcast sends the correct
day's message.
"""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.contacts.app.main import app as contacts_app

campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)
contacts_client = TestClient(contacts_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"


def _enroll(contact_id: str, step: str | None = None) -> dict:
    payload = {
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
    }
    if step:
        payload["current_step"] = step
    resp = campaigns_client.post("/campaigns/enroll", json=payload)
    assert resp.status_code == 201
    return resp.json()


def _grant_consent(contact_id: str) -> None:
    resp = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "test",
    })
    assert resp.status_code == 201


def _broadcast() -> dict:
    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    return resp.json()


def test_step_advances_from_j7_to_j6_after_broadcast():
    """J-7 → J-6 after first broadcast."""
    _enroll("ct_prog_001")
    _grant_consent("ct_prog_001")

    result = _broadcast()
    assert result["queued"] == 1
    assert result["messages"][0]["template_key"] == "welcome_j7"

    # Second broadcast should use J-6 template
    result2 = _broadcast()
    assert result2["queued"] == 1
    assert result2["messages"][0]["template_key"] == "content_j6"


def test_step_advances_through_full_journey():
    """Contact progresses through all journey steps: J-7 → J-6 → DAY_1 → DAY_2 → DAY_3 → completed."""
    _enroll("ct_prog_full")
    _grant_consent("ct_prog_full")

    expected = [
        "welcome_j7",
        "content_j6",
        "challenge_day_1",
        "challenge_day_2_catchup",   # no attendance event → catchup
        "challenge_day_3_catchup",   # no attendance event → catchup
    ]
    for expected_tpl in expected:
        result = _broadcast()
        assert result["queued"] == 1, f"Expected 1 message, got {result['queued']} (step expected: {expected_tpl})"
        assert result["messages"][0]["template_key"] == expected_tpl

    # After DAY_3, contact is 'completed' — no more messages
    result_after = _broadcast()
    assert result_after["queued"] == 0


def test_completed_contact_receives_no_further_messages():
    """A contact at 'completed' step is silently skipped on broadcast."""
    _enroll("ct_prog_done", step="DAY_3")
    _grant_consent("ct_prog_done")

    # Send DAY_3 — advances to completed
    first = _broadcast()
    assert first["queued"] == 1

    # Now the contact is at 'completed' — no message
    second = _broadcast()
    assert second["queued"] == 0
