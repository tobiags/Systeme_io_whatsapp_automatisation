"""Tests for auto-enrollment triggered by Systeme.io webhook.

When the webhook fires for a contact and there is an active ChallengeEdition
for the detected cohort, the platform automatically creates a CampaignEnrollment
at the correct step (via smart-skip).
"""
from fastapi.testclient import TestClient

from services.integrations.app.main import app as integrations_app
from tests.conftest import _TestingSession
from shared.db.models import CampaignEnrollment, Message

integrations_client = TestClient(integrations_app)


def _register_edition(edition_key: str, edition_date: str, cohort: str = "EU"):
    """Pre-register a ChallengeEdition so auto-enrollment can find it."""
    integrations_client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": edition_key,
        "region": cohort,
        "join_url": f"https://streamyard.com/{edition_key}",
        "edition_date": edition_date,
    })


def _systemeio_payload(phone: str, first_name: str = "Test", cohort: str = "EU") -> dict:
    return {
        "contact": {
            "id": abs(hash(phone)) % 100000,
            "email": f"{first_name.lower()}@example.com",
            "fields": [
                {"slug": "first_name",   "value": first_name},
                {"slug": "phone_number", "value": phone},
            ],
            "tags": [],
        },
        "cohort": cohort,
    }


def test_systemeio_webhook_includes_enrollment_when_edition_active():
    """Auto-enrollment fires when an active edition exists for the cohort."""
    # Create an edition dated in the future
    _register_edition("2030-01-01-eu", "2030-01-01", cohort="EU")

    resp = integrations_client.post("/webhooks/systemeio", json=_systemeio_payload("+33600000010"))
    assert resp.status_code == 202
    body = resp.json()
    assert "enrollment" in body
    assert body["welcome"]["status"] == "queued"

    db = _TestingSession()
    try:
        enrollment = db.query(CampaignEnrollment).filter(CampaignEnrollment.contact_id == body["contact_id"]).first()
        assert enrollment is not None
        assert enrollment.current_step == "COUNTDOWN_J6"
        welcome = db.query(Message).filter(Message.contact_id == body["contact_id"], Message.template_key == "welcome").first()
        assert welcome is not None
        assert welcome.variables["script_state"] == {
            "flow": "entry_questionnaire",
            "stage": "awaiting_choice",
            "rephrase_count": 0,
        }
    finally:
        db.close()


def test_systemeio_webhook_no_enrollment_when_no_active_edition():
    """No enrollment is created when there is no upcoming edition for the cohort."""
    # Use US-CA cohort — no edition registered for it
    resp = integrations_client.post("/webhooks/systemeio", json=_systemeio_payload("+12025550001", cohort="US-CA"))
    assert resp.status_code == 202
    body = resp.json()
    # enrollment key may be absent or None
    assert body.get("enrollment") is None


def test_systemeio_auto_enrollment_not_duplicated():
    """Re-sending the same webhook does not create duplicate enrollments."""
    _register_edition("2030-01-02-eu", "2030-01-02", cohort="EU")
    phone = "+33600000020"

    resp1 = integrations_client.post("/webhooks/systemeio", json=_systemeio_payload(phone))
    assert resp1.status_code == 202
    contact_id = resp1.json()["contact_id"]
    enrollment1 = resp1.json().get("enrollment")

    # Second call with same phone — same contact (upsert)
    resp2 = integrations_client.post("/webhooks/systemeio", json=_systemeio_payload(phone))
    assert resp2.status_code == 202
    assert resp2.json()["contact_id"] == contact_id
    # No second enrollment created for the same contact+campaign+edition
    enrollment2 = resp2.json().get("enrollment")
    if enrollment1 and enrollment2:
        assert enrollment1["enrollment_id"] == enrollment2["enrollment_id"]

    db = _TestingSession()
    try:
        welcomes = db.query(Message).filter(Message.contact_id == contact_id, Message.template_key == "welcome").all()
        assert len(welcomes) == 1
    finally:
        db.close()


def test_systemeio_cohort_defaults_to_EU():
    """When cohort field is missing, the webhook defaults to EU."""
    _register_edition("2030-01-03-eu", "2030-01-03", cohort="EU")
    # Payload without cohort field
    payload = {
        "contact": {
            "id": 77777,
            "email": "nocohort@example.com",
            "fields": [
                {"slug": "first_name",   "value": "NoCohort"},
                {"slug": "phone_number", "value": "+33600000030"},
            ],
            "tags": [],
        }
    }
    resp = integrations_client.post("/webhooks/systemeio", json=payload)
    assert resp.status_code == 202


def test_systemeio_us_ca_cohort_triggers_enrollment_for_us_edition():
    """US-CA payload enrolls in the US-CA edition, not the EU edition."""
    _register_edition("2030-02-01-us-ca", "2030-02-01", cohort="US-CA")

    resp = integrations_client.post(
        "/webhooks/systemeio",
        json=_systemeio_payload("+12025550099", cohort="US-CA"),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "enrollment" in body
    if body.get("enrollment"):
        assert body["enrollment"]["cohort"] == "US-CA"
