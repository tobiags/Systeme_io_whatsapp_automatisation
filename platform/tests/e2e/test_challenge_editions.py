"""Tests for ChallengeEdition model, StreamYard persistence, and edition_key on enrollments."""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.integrations.app.main import app as integrations_app

integrations_client = TestClient(integrations_app)
campaigns_client = TestClient(campaigns_app)

STREAMYARD_PAYLOAD = {
    "challenge_key": "challenge-amazon-fba",
    "edition_key": "2026-05-08-eu",
    "region": "EU",
    "join_url": "https://streamyard.com/abc123",
}


def test_streamyard_session_is_persisted():
    resp = integrations_client.post("/webhooks/streamyard/session", json=STREAMYARD_PAYLOAD)
    assert resp.status_code == 202
    body = resp.json()
    assert body["edition_key"] == "2026-05-08-eu"
    assert body["join_url"] == "https://streamyard.com/abc123"
    assert body["stored"] is True


def test_streamyard_session_upserts_existing_edition():
    integrations_client.post("/webhooks/streamyard/session", json=STREAMYARD_PAYLOAD)
    # Update link for same edition
    updated = {**STREAMYARD_PAYLOAD, "join_url": "https://streamyard.com/updated_link"}
    resp = integrations_client.post("/webhooks/streamyard/session", json=updated)
    assert resp.status_code == 202
    assert resp.json()["join_url"] == "https://streamyard.com/updated_link"


def test_list_editions_returns_registered_sessions():
    integrations_client.post("/webhooks/streamyard/session", json=STREAMYARD_PAYLOAD)
    resp = integrations_client.get("/webhooks/streamyard/editions")
    assert resp.status_code == 200
    editions = resp.json()
    assert len(editions) >= 1
    keys = [e["edition_key"] for e in editions]
    assert "2026-05-08-eu" in keys


def test_campaign_enrollment_stores_edition_key():
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": "ct_ed_001",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU",
        "edition_key": "2026-05-08-eu",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["edition_key"] == "2026-05-08-eu"


def test_campaign_enrollment_without_edition_key_still_works():
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": "ct_ed_002",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU",
    })
    assert resp.status_code == 201
    assert resp.json()["edition_key"] is None
