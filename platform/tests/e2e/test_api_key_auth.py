"""Tests for X-API-Key authentication middleware on the API Gateway.

When PLATFORM_API_KEY is configured:
  - All protected endpoints return 401 without the header.
  - All protected endpoints return 2xx with the correct header.
  - /health is always public (no key required).
  - POST /webhooks/systemeio and POST /webhooks/wati are always public.
"""
import pytest
from fastapi.testclient import TestClient

from services.api_gateway.app.main import app
from shared.config.settings import settings

client = TestClient(app, raise_server_exceptions=False)

_TEST_KEY = "test-secret-key-xyz"


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Activate API key auth for the duration of each test."""
    monkeypatch.setattr(settings, "platform_api_key", _TEST_KEY)
    yield
    monkeypatch.setattr(settings, "platform_api_key", "")


# ── Public paths are always accessible ───────────────────────────────────────

def test_health_is_public_no_key_needed():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_systemeio_webhook_is_public():
    """Systeme.io calls this without our key — must not be blocked."""
    resp = client.post("/webhooks/systemeio", json={
        "email": "test@example.com",
        "fields": {"first_name": "Test"},
    })
    # 202 Accepted (or any non-401)
    assert resp.status_code != 401


def test_wati_inbound_webhook_is_public():
    """Wati calls this without our key — must not be blocked."""
    resp = client.post("/webhooks/wati", json={
        "waId": "+33600000099",
        "text": {"body": "quand ca commence ?"},
    })
    assert resp.status_code != 401


# ── Protected paths require the key ──────────────────────────────────────────

def test_dashboard_returns_401_without_key():
    resp = client.get("/dashboard/summary")
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


def test_contacts_returns_401_without_key():
    resp = client.get("/contacts")
    assert resp.status_code == 401


def test_wati_queue_returns_401_without_key():
    """The operator queue is protected — not the same path as the inbound webhook."""
    resp = client.get("/webhooks/wati/queue")
    assert resp.status_code == 401


def test_scoring_events_returns_401_without_key():
    resp = client.post("/scores/events", json={"contact_id": "ct_x", "event_type": "registered"})
    assert resp.status_code == 401


# ── Correct key grants access ─────────────────────────────────────────────────

def test_dashboard_accessible_with_correct_key():
    resp = client.get("/dashboard/summary", headers={"X-API-Key": _TEST_KEY})
    assert resp.status_code == 200


def test_contacts_accessible_with_correct_key():
    resp = client.get("/contacts", headers={"X-API-Key": _TEST_KEY})
    assert resp.status_code == 200


def test_wati_queue_accessible_with_correct_key():
    resp = client.get("/webhooks/wati/queue", headers={"X-API-Key": _TEST_KEY})
    assert resp.status_code == 200


def test_wrong_key_returns_401():
    resp = client.get("/contacts", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


# ── Auth disabled when key is empty (local dev / tests) ──────────────────────

def test_auth_disabled_when_key_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "platform_api_key", "")
    resp = client.get("/contacts")  # no header
    assert resp.status_code == 200
