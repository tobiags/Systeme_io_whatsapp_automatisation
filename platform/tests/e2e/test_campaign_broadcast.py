"""Tests for POST /campaigns/broadcast — queue messages for all enrolled contacts."""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app

campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"


def _enroll(contact_id: str):
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
    })
    assert resp.status_code == 201
    return resp.json()


def _grant_consent(contact_id: str):
    resp = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "test",
    })
    assert resp.status_code == 201


def test_broadcast_empty_cohort_returns_zero():
    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": "UNKNOWN_COHORT",
    })
    assert resp.status_code == 200
    assert resp.json()["queued"] == 0
    assert resp.json()["messages"] == []


def test_broadcast_queues_message_for_each_enrollment():
    for cid in ("ct_brd_001", "ct_brd_002", "ct_brd_003"):
        _enroll(cid)
        _grant_consent(cid)

    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["queued"] == 3
    contact_ids = [m["contact_id"] for m in body["messages"]]
    assert "ct_brd_001" in contact_ids
    assert "ct_brd_002" in contact_ids
    assert "ct_brd_003" in contact_ids


def test_broadcast_uses_current_step_template():
    _enroll("ct_brd_tpl")
    _grant_consent("ct_brd_tpl")

    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    msg = resp.json()["messages"][0]
    # First step in DEFAULT_JOURNEY is J-7 → welcome_j7
    assert msg["template_key"] == "welcome_j7"
    assert msg["message_id"].startswith("msg_")


def test_broadcast_skips_contact_without_consent():
    """Contacts without opt-in consent must be excluded from broadcast (spec §4.3)."""
    _enroll("ct_brd_noconsent")
    # No consent granted

    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["queued"] == 0
    assert body["skipped_no_consent"] == 1


def test_broadcast_returns_skipped_count():
    """Response includes skipped_no_consent counter."""
    _enroll("ct_brd_skip1")
    _enroll("ct_brd_skip2")
    _grant_consent("ct_brd_skip1")
    # ct_brd_skip2 has no consent

    resp = campaigns_client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["queued"] == 1
    assert body["skipped_no_consent"] == 1
