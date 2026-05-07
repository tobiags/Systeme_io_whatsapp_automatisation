"""Tests for POST /campaigns/broadcast — queue messages for all enrolled contacts."""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app

client = TestClient(campaigns_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"


def _enroll(contact_id: str):
    resp = client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
    })
    assert resp.status_code == 201
    return resp.json()


def test_broadcast_empty_cohort_returns_zero():
    resp = client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": "UNKNOWN_COHORT",
    })
    assert resp.status_code == 200
    assert resp.json()["queued"] == 0
    assert resp.json()["messages"] == []


def test_broadcast_queues_message_for_each_enrollment():
    _enroll("ct_brd_001")
    _enroll("ct_brd_002")
    _enroll("ct_brd_003")

    resp = client.post("/campaigns/broadcast", json={
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

    resp = client.post("/campaigns/broadcast", json={
        "campaign_key": CAMPAIGN_KEY,
        "cohort": COHORT,
    })
    assert resp.status_code == 200
    msg = resp.json()["messages"][0]
    # First step in DEFAULT_JOURNEY is J-7 → welcome_j7
    assert msg["template_key"] == "welcome_j7"
    assert msg["message_id"].startswith("msg_")
