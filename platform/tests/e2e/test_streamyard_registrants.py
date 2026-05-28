"""Tests for POST /webhooks/streamyard/registrants — StreamYard registration tracking."""
from fastapi.testclient import TestClient

from services.integrations.app.main import app as integrations_app

client = TestClient(integrations_app)

EDITION_KEY = "2026-05-07-eu"


def _register_contact(phone: str) -> str:
    from services.contacts.app.main import app as contacts_app
    contacts_client = TestClient(contacts_app)
    resp = contacts_client.post("/contacts", json={
        "phone": phone,
        "first_name": "Test",
        "source": "test",
    })
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_registrants_records_day1_event():
    """Posting registrants for day 1 creates a day1_streamyard_registered ScoreEvent."""
    phone = "33800000201"
    contact_id = _register_contact(phone)

    resp = client.post("/webhooks/streamyard/registrants", json={
        "edition_key": EDITION_KEY,
        "day_number": 1,
        "registrants": [phone],
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["event_type"] == "day1_streamyard_registered"
    assert body["recorded"] == 1
    assert body["not_found"] == 0
    assert contact_id in body["contact_ids"]


def test_registrants_is_idempotent():
    """Posting the same registrant twice does not create duplicate ScoreEvents."""
    phone = "33800000202"
    _register_contact(phone)

    payload = {
        "edition_key": EDITION_KEY,
        "day_number": 2,
        "registrants": [phone],
    }
    client.post("/webhooks/streamyard/registrants", json=payload)
    resp2 = client.post("/webhooks/streamyard/registrants", json=payload)

    assert resp2.status_code == 202
    body = resp2.json()
    assert body["recorded"] == 0
    assert body["already_recorded"] == 1


def test_registrants_unknown_phone_reports_not_found():
    """Phones not in Contact table are reported in not_found."""
    resp = client.post("/webhooks/streamyard/registrants", json={
        "edition_key": EDITION_KEY,
        "day_number": 3,
        "registrants": ["99988877766"],
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["not_found"] == 1
    assert body["recorded"] == 0


def test_registrants_day_number_validation():
    """day_number must be 1, 2, or 3 — values outside range are rejected."""
    resp = client.post("/webhooks/streamyard/registrants", json={
        "edition_key": EDITION_KEY,
        "day_number": 4,
        "registrants": [],
    })
    assert resp.status_code == 422


def test_registrants_batch_mixed():
    """Batch with known + unknown phones → correct counts."""
    known_phone = "33800000203"
    _register_contact(known_phone)

    resp = client.post("/webhooks/streamyard/registrants", json={
        "edition_key": EDITION_KEY,
        "day_number": 1,
        "registrants": [known_phone, "00011122233"],
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["recorded"] == 1
    assert body["not_found"] == 1
