"""Tests for POST /webhooks/streamyard/attendance — live attendance tracking."""
from fastapi.testclient import TestClient

from services.integrations.app.main import app as integrations_app
from services.scoring.app.main import app as scoring_app

client = TestClient(integrations_app)
scoring_client = TestClient(scoring_app)

EDITION_KEY = "2026-05-07-eu"


def _register_contact(phone: str) -> str:
    """Create a contact via the contacts service. Returns the generated contact_id."""
    from services.contacts.app.main import app as contacts_app
    contacts_client = TestClient(contacts_app)
    resp = contacts_client.post("/contacts", json={
        "phone": phone,
        "first_name": "Test",
        "source": "test",
    })
    # 201 = created, 200 = upserted (already exists) — both are fine
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_attendance_records_day1_event():
    """Posting attendance for day 1 creates a day1_live_joined ScoreEvent."""
    phone = "33700000101"
    contact_id = _register_contact(phone)

    resp = client.post("/webhooks/streamyard/attendance", json={
        "edition_key": EDITION_KEY,
        "day_number": 1,
        "attendees": [phone],
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["event_type"] == "day1_live_joined"
    assert body["recorded"] == 1
    assert body["not_found"] == 0
    assert contact_id in body["contact_ids"]


def test_attendance_is_idempotent():
    """Posting the same attendance twice does not create duplicate ScoreEvents."""
    phone = "33700000102"
    _register_contact(phone)

    payload = {
        "edition_key": EDITION_KEY,
        "day_number": 2,
        "attendees": [phone],
    }
    client.post("/webhooks/streamyard/attendance", json=payload)
    resp2 = client.post("/webhooks/streamyard/attendance", json=payload)

    assert resp2.status_code == 202
    body = resp2.json()
    assert body["recorded"] == 0
    assert body["already_recorded"] == 1


def test_attendance_unknown_phone_reports_not_found():
    """Phones not in the Contact table are reported in not_found."""
    resp = client.post("/webhooks/streamyard/attendance", json={
        "edition_key": EDITION_KEY,
        "day_number": 3,
        "attendees": ["99999999999"],
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["not_found"] == 1
    assert body["recorded"] == 0


def test_attendance_batch_mixed():
    """Batch with known + unknown phones → correct counts."""
    known_phone = "33700000103"
    _register_contact(known_phone)

    resp = client.post("/webhooks/streamyard/attendance", json={
        "edition_key": EDITION_KEY,
        "day_number": 1,
        "attendees": [known_phone, "00000000000"],
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["recorded"] == 1
    assert body["not_found"] == 1


def test_attendance_day_number_validation():
    """day_number must be 1, 2, or 3 — values outside range are rejected."""
    resp = client.post("/webhooks/streamyard/attendance", json={
        "edition_key": EDITION_KEY,
        "day_number": 5,
        "attendees": [],
    })
    assert resp.status_code == 422
