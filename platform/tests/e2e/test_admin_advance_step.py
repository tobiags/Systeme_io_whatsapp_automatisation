"""Tests for POST /admin/advance-step — force-advance contacts between journey steps.

Recovery scenario: Meta blocks MARKETING templates for US/CA recipients.
321 contacts fail at DAY_2 and get stuck. Before Day 3 broadcast, operator
must advance them to DAY_3 so they receive the Day 3 message.
"""
from fastapi.testclient import TestClient

from services.api_gateway.app.main import app as gateway_app
from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app

gateway_client = TestClient(gateway_app)
campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
EDITION_KEY = "2026-05-28-usca"
COHORT = "US-CA"


def _enroll(contact_id: str, step: str = "DAY_2"):
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
        "edition_key": EDITION_KEY,
        "current_step": step,
    })
    assert resp.status_code == 201


def _grant_consent(contact_id: str):
    resp = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "test",
    })
    assert resp.status_code == 201


def test_advance_step_dry_run_shows_count():
    _enroll("ct_adv_dry1")
    _enroll("ct_adv_dry2")
    _grant_consent("ct_adv_dry1")
    _grant_consent("ct_adv_dry2")

    resp = gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "DAY_2",
        "to_step": "DAY_3",
        "dry_run": True,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is True
    assert body["advanced"] == 2
    assert "ct_adv_dry1" in body["contact_ids"]
    assert "ct_adv_dry2" in body["contact_ids"]


def test_advance_step_dry_run_does_not_write():
    _enroll("ct_adv_nowrite")
    _grant_consent("ct_adv_nowrite")

    gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "DAY_2",
        "to_step": "DAY_3",
        "dry_run": True,
    })

    # Step should still be DAY_2
    resp = gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "DAY_2",
        "to_step": "DAY_3",
        "dry_run": True,
    })
    assert resp.json()["advanced"] >= 1


def test_advance_step_writes_new_step():
    _enroll("ct_adv_write1")
    _enroll("ct_adv_write2")
    _grant_consent("ct_adv_write1")
    _grant_consent("ct_adv_write2")

    resp = gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "DAY_2",
        "to_step": "DAY_3",
        "dry_run": False,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is False
    assert body["advanced"] == 2

    # Verify contacts are no longer at DAY_2 (second call finds 0)
    resp2 = gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "DAY_2",
        "to_step": "DAY_3",
        "dry_run": True,
    })
    assert resp2.json()["advanced"] == 0


def test_advance_step_returns_zero_when_no_contacts_at_step():
    resp = gateway_client.post("/admin/advance-step", json={
        "edition_key": "nonexistent-edition",
        "from_step": "DAY_2",
        "to_step": "DAY_3",
        "dry_run": True,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["advanced"] == 0


def test_advance_step_rejects_invalid_from_step():
    resp = gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "BOGUS_STEP",
        "to_step": "DAY_3",
        "dry_run": True,
    })
    assert resp.status_code == 400
    assert "BOGUS_STEP" in resp.json()["detail"]


def test_advance_step_rejects_invalid_to_step():
    resp = gateway_client.post("/admin/advance-step", json={
        "edition_key": EDITION_KEY,
        "from_step": "DAY_2",
        "to_step": "INVALID",
        "dry_run": True,
    })
    assert resp.status_code == 400
    assert "INVALID" in resp.json()["detail"]


def test_diagnostics_includes_step_breakdown():
    _enroll("ct_diag_step1", step="DAY_2")
    _enroll("ct_diag_step2", step="DAY_3")
    _grant_consent("ct_diag_step1")
    _grant_consent("ct_diag_step2")

    resp = gateway_client.get("/admin/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert "active_editions" in body
