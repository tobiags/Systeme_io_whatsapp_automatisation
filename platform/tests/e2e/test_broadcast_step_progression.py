"""Tests for journey step progression after broadcast."""
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

import services.campaigns.app.main as campaigns_main
from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.contacts.app.main import app as contacts_app
from shared.db.models import ChallengeEdition
from tests.conftest import _TestingSession

campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)
contacts_client = TestClient(contacts_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"
EDITION_KEY = "2026-05-24-eu"
EDITION_DATE = "2026-05-24"


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


def _enroll(contact_id: str, step: str | None = None, edition_key: str = EDITION_KEY) -> dict:
    payload = {
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
        "edition_key": edition_key,
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


def _broadcast(local_day: date) -> dict:
    with patch("services.campaigns.app.main._local_broadcast_date", return_value=local_day):
        resp = campaigns_client.post("/campaigns/broadcast", json={
            "campaign_key": CAMPAIGN_KEY,
            "cohort": COHORT,
            "edition_key": EDITION_KEY,
        })
    assert resp.status_code == 200
    return resp.json()


def test_step_advances_from_welcome_to_countdown_j1_after_broadcast():
    """WELCOME -> COUNTDOWN_J1 -> DAY_1 on the real v7 dates."""
    _seed_edition()
    _enroll("ct_prog_001")
    _grant_consent("ct_prog_001")

    result = _broadcast(date(2026, 5, 22))
    assert result["queued"] == 1
    assert result["messages"][0]["template_key"] == "welcome_v7"

    result2 = _broadcast(date(2026, 5, 23))
    assert result2["queued"] == 1
    assert result2["messages"][0]["template_key"] == "countdown_j1_v7"


def test_step_advances_through_full_journey():
    """Contact progresses through all v7 journey steps on the no-show path."""
    _seed_edition()
    _enroll("ct_prog_full")
    _grant_consent("ct_prog_full")

    expected = [
        (date(2026, 5, 22), "welcome_v7"),
        (date(2026, 5, 23), "countdown_j1_v7"),
        (date(2026, 5, 24), "live_day1_v7"),
        (date(2026, 5, 25), "live_day2_not_registered_v7"),
        (date(2026, 5, 26), "live_day3_not_registered_v7"),
        (date(2026, 5, 27), "post_replay_v7"),
        (date(2026, 5, 28), "post_testimonials_v7"),
        (date(2026, 5, 29), "post_closer_v7"),
        (date(2026, 5, 30), "post_closer_call_v7"),
    ]
    for local_day, expected_tpl in expected:
        result = _broadcast(local_day)
        assert result["queued"] == 1, (
            f"Expected 1 message, got {result['queued']} (expected tpl: {expected_tpl})"
        )
        assert result["messages"][0]["template_key"] == expected_tpl, (
            f"Expected {expected_tpl}, got {result['messages'][0]['template_key']}"
        )

    result_after = _broadcast(date(2026, 5, 31))
    assert result_after["queued"] == 0


def test_completed_contact_receives_no_further_messages():
    """A contact at AFTER_3 completes after the J+4 post-challenge send."""
    _seed_edition()
    _enroll("ct_prog_done", step="AFTER_3")
    _grant_consent("ct_prog_done")

    first = _broadcast(date(2026, 5, 30))
    assert first["queued"] == 1

    second = _broadcast(date(2026, 5, 31))
    assert second["queued"] == 0


def test_paid_offer_contact_is_completed_and_skipped():
    _seed_edition()
    _enroll("ct_prog_paid")
    _grant_consent("ct_prog_paid")

    from services.scoring.app.main import app as scoring_app
    scoring_client = TestClient(scoring_app)
    resp = scoring_client.post("/scores/events", json={
        "contact_id": "ct_prog_paid",
        "event_type": "paid_offer",
    })
    assert resp.status_code in (200, 201)

    result = _broadcast(date(2026, 5, 22))
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

    _seed_edition()
    _enroll("ct_prog_failed")
    _grant_consent("ct_prog_failed")

    first = _broadcast(date(2026, 5, 22))
    assert first["queued"] == 1
    assert first["messages"][0]["template_key"] == "welcome_v7"
    assert first["messages"][0]["status"] == "failed"

    second = _broadcast(date(2026, 5, 23))
    assert second["queued"] == 1
    assert second["messages"][0]["template_key"] == "welcome_v7"
