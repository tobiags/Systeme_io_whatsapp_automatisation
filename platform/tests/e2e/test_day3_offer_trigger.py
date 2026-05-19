"""Tests for POST /campaigns/trigger/day3-offer — manual H+2 Day-3 trigger."""
from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.contacts.app.main import app as contacts_app
from services.integrations.app.main import app as integrations_app
from services.consent.app.main import app as consent_app
from services.scoring.app.main import app as scoring_app

campaigns_client = TestClient(campaigns_app)
contacts_client = TestClient(contacts_app)
integrations_client = TestClient(integrations_app)
consent_client = TestClient(consent_app)
scoring_client = TestClient(scoring_app)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def _setup_contact(phone: str, first_name: str = "Test") -> str:
    """Create contact via systemeio webhook (auto-creates opted_in consent)."""
    resp = integrations_client.post("/webhooks/systemeio", json={
        "email": f"{first_name.lower()}@example.com",
        "phone_number": phone,
        "first_name": first_name,
    })
    assert resp.status_code == 202
    return resp.json()["contact_id"]


def _setup_contact_no_consent(phone: str, first_name: str = "Test") -> str:
    """Create contact directly (no consent) — use when testing the consent gate."""
    resp = contacts_client.post("/contacts", json={
        "phone": phone,
        "first_name": first_name,
        "source": "test",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def _give_consent(contact_id: str):
    resp = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "systemeio",
    })
    assert resp.status_code == 201


def _enroll(contact_id: str, campaign_key: str = "challenge-amazon-fba",
            edition_key: str = "2026-05-08-eu"):
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": campaign_key,
        "region": "EU",
        "edition_key": edition_key,
    })
    assert resp.status_code == 201


def _register_day3(contact_id: str):
    """Fire day3_streamyard_registered score event for the contact."""
    resp = scoring_client.post("/scores/events", json={
        "contact_id": contact_id,
        "event_type": "day3_streamyard_registered",
    })
    assert resp.status_code in (200, 201)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_day3_offer_sends_only_to_registered_contacts():
    """Only contacts with day3_streamyard_registered receive live_day3_offer_hplus2."""
    campaign_key = "registration-filter-test-campaign"

    # Contact A — registered for Day 3
    ct_a = _setup_contact("+33700000100", "Alice")
    _give_consent(ct_a)
    _enroll(ct_a, campaign_key=campaign_key)
    _register_day3(ct_a)

    # Contact B — NOT registered for Day 3 (no score event)
    ct_b = _setup_contact("+33700000101", "Bob")
    _give_consent(ct_b)
    _enroll(ct_b, campaign_key=campaign_key)

    resp = campaigns_client.post("/campaigns/trigger/day3-offer", json={
        "campaign_key": campaign_key,
        "cohort": "EU",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] >= 1
    assert body["skipped_not_registered"] >= 1
    assert body["template_key"] == "live_day3_offer_hplus2"


def test_day3_offer_respects_consent_gate():
    """Contacts without opt-in consent are skipped."""
    campaign_key = "consent-gate-test-campaign"
    # Use direct contacts API — does NOT auto-create consent (unlike systemeio webhook)
    ct = _setup_contact_no_consent("+33700000200", "Chloe")
    _enroll(ct, campaign_key=campaign_key)
    _register_day3(ct)

    resp = campaigns_client.post("/campaigns/trigger/day3-offer", json={
        "campaign_key": campaign_key,
        "cohort": "EU",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["skipped_no_consent"] >= 1


def test_day3_offer_with_edition_key_filter():
    """Passing edition_key restricts the trigger to that edition only."""
    edition_key = "2026-08-01-eu"
    ct = _setup_contact("+33700000300", "Denis")
    _give_consent(ct)
    _enroll(ct, edition_key=edition_key)
    _register_day3(ct)

    resp = campaigns_client.post("/campaigns/trigger/day3-offer", json={
        "campaign_key": "challenge-amazon-fba",
        "cohort": "EU",
        "edition_key": edition_key,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["template_key"] == "live_day3_offer_hplus2"


def test_day3_offer_returns_zero_when_no_enrolled_contacts():
    """Endpoint returns zero without crashing when no contacts are enrolled."""
    resp = campaigns_client.post("/campaigns/trigger/day3-offer", json={
        "campaign_key": "nonexistent-campaign",
        "cohort": "EU",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] == 0


def test_day3_offer_skips_contacts_who_already_paid():
    campaign_key = "paid-offer-filter-test-campaign"
    ct = _setup_contact("+33700000999", "Eva")
    _give_consent(ct)
    _enroll(ct, campaign_key=campaign_key)
    _register_day3(ct)

    score_resp = scoring_client.post("/scores/events", json={
        "contact_id": ct,
        "event_type": "paid_offer",
    })
    assert score_resp.status_code in (200, 201)

    resp = campaigns_client.post("/campaigns/trigger/day3-offer", json={
        "campaign_key": campaign_key,
        "cohort": "EU",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] == 0
    assert body["skipped_paid_offer"] >= 1
