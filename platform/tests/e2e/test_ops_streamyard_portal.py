"""Tests for operator-friendly StreamYard endpoints protected by OPS_PORTAL_TOKEN."""
import pytest
from fastapi.testclient import TestClient

from services.api_gateway.app.main import app
from services.contacts.app.main import app as contacts_app
from shared.config.settings import settings

ops_client = TestClient(app, raise_server_exceptions=False)
contacts_client = TestClient(contacts_app)


@pytest.fixture(autouse=True)
def _set_ops_token(monkeypatch):
    monkeypatch.setattr(settings, "ops_portal_token", "ops-secret-token")
    monkeypatch.setattr(settings, "platform_api_key", "platform-secret")
    yield
    monkeypatch.setattr(settings, "ops_portal_token", "")
    monkeypatch.setattr(settings, "platform_api_key", "")


def test_ops_session_requires_valid_ops_token():
    resp = ops_client.post("/ops/streamyard/session", json={
        "edition_key": "2030-06-01-eu",
        "region": "EU",
        "day_number": 1,
        "join_url": "https://streamyard.com/day1",
    })
    assert resp.status_code == 401


def test_ops_session_accepts_query_token():
    resp = ops_client.post("/ops/streamyard/session?token=ops-secret-token", json={
        "edition_key": "2030-06-01-eu",
        "region": "EU",
        "day_number": 1,
        "join_url": "https://streamyard.com/day1",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["stored"] is True
    assert body["day_number"] == 1


def test_ops_registrants_accepts_header_token_and_records_contacts():
    contacts_client.post("/contacts", json={
        "phone": "22901020304",
        "first_name": "Lea",
        "source": "test",
    })
    resp = ops_client.post(
        "/ops/streamyard/registrants",
        headers={"X-Ops-Token": "ops-secret-token"},
        json={
            "edition_key": "2030-06-01-eu",
            "day_number": 1,
            "registrants": ["22901020304", "22999999999"],
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["recorded"] == 1
    assert body["not_found"] == 1


def test_ops_attendance_accepts_header_token_and_records_contacts():
    contacts_client.post("/contacts", json={
        "phone": "22901020305",
        "first_name": "Mia",
        "source": "test",
    })
    resp = ops_client.post(
        "/ops/streamyard/attendance",
        headers={"X-Ops-Token": "ops-secret-token"},
        json={
            "edition_key": "2030-06-01-eu",
            "day_number": 1,
            "attendees": ["22901020305"],
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["recorded"] == 1
    assert body["event_type"] == "day1_live_joined"
