"""Tests for journey step progression after broadcast.

After each broadcast, a contact's current_step must advance to the next step
in the DEFAULT_JOURNEY sequence so that the next broadcast sends the correct
day's message.
"""
from fastapi.testclient import TestClient

import services.campaigns.app.main as campaigns_main
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


def test_step_advances_from_welcome_to_countdown_j6_after_broadcast():
    """WELCOME → COUNTDOWN_J6 after first broadcast."""
    _enroll("ct_prog_001")
    _grant_consent("ct_prog_001")

    result = _broadcast()
    assert result["queued"] == 1
    assert result["messages"][0]["template_key"] == "welcome"

    # Second broadcast should use COUNTDOWN_J6 template
    result2 = _broadcast()
    assert result2["queued"] == 1
    assert result2["messages"][0]["template_key"] == "countdown_j6"


def test_step_advances_through_full_journey():
    """
    Contact progresses through all journey steps — no-show path (no attendance/registration):
    WELCOME → J6 → J5 → J4 → J3 → J2 → J1 →
    DAY_1 → DAY_2 (not_registered) → DAY_3 (not_registered) →
    AFTER_1 (absent replay) → AFTER_2 → AFTER_3 → AFTER_4 → completed
    """
    _enroll("ct_prog_full")
    _grant_consent("ct_prog_full")

    expected = [
        "welcome",
        "countdown_j6",
        "countdown_j5",
        "countdown_j4",
        "countdown_j3",
        "countdown_j2",
        "countdown_j1",
        "live_day1",
        "live_day2_not_registered",
        "live_day3_not_registered",
        "post_recap_not_registered",
        "post_testimonials",
        "post_inaction_reason",
        "post_closer_call",
    ]
    for expected_tpl in expected:
        result = _broadcast()
        assert result["queued"] == 1, (
            f"Expected 1 message, got {result['queued']} (expected tpl: {expected_tpl})"
        )
        assert result["messages"][0]["template_key"] == expected_tpl, (
            f"Expected {expected_tpl}, got {result['messages'][0]['template_key']}"
        )

    # After AFTER_4, contact is 'completed' — no more messages
    result_after = _broadcast()
    assert result_after["queued"] == 0


def test_completed_contact_receives_no_further_messages():
    """A contact at 'completed' step is silently skipped on broadcast."""
    _enroll("ct_prog_done", step="AFTER_4")
    _grant_consent("ct_prog_done")

    # Send AFTER_4 — advances to completed
    first = _broadcast()
    assert first["queued"] == 1

    # Now the contact is at 'completed' — no message
    second = _broadcast()
    assert second["queued"] == 0


def test_paid_offer_contact_is_completed_and_skipped():
    _enroll("ct_prog_paid")
    _grant_consent("ct_prog_paid")

    from services.scoring.app.main import app as scoring_app
    scoring_client = TestClient(scoring_app)
    resp = scoring_client.post("/scores/events", json={
        "contact_id": "ct_prog_paid",
        "event_type": "paid_offer",
    })
    assert resp.status_code in (200, 201)

    result = _broadcast()
    assert result["queued"] == 0
    assert result["skipped_paid_offer"] >= 1


def test_failed_delivery_does_not_advance_step(monkeypatch):
    class _FailingProvider:
        def send_template(self, phone, template_key, variables):
            return {
                "status": "failed",
                "provider": "wati",
                "provider_message_id": "failed-001",
            }

    monkeypatch.setattr(campaigns_main, "_get_provider", lambda: _FailingProvider())

    _enroll("ct_prog_failed")
    _grant_consent("ct_prog_failed")

    first = _broadcast()
    assert first["queued"] == 1
    assert first["messages"][0]["template_key"] == "welcome"
    assert first["messages"][0]["status"] == "failed"

    second = _broadcast()
    assert second["queued"] == 1
    assert second["messages"][0]["template_key"] == "welcome"
