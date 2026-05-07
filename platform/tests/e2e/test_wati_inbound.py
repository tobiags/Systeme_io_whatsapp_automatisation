"""Tests for POST /webhooks/wati — inbound WhatsApp message processing."""
from fastapi.testclient import TestClient

from services.integrations.app.main import app as integrations_app

client = TestClient(integrations_app)

# Standard Wati webhook payload shape
WATI_PAYLOAD = {
    "waId": "+22900000099",
    "text": {"body": "Bonjour, c'est quoi le challenge ?"},
}


def test_wati_inbound_returns_reply():
    resp = client.post("/webhooks/wati", json=WATI_PAYLOAD)
    assert resp.status_code == 202
    body = resp.json()
    assert body["phone"] == "+22900000099"
    assert isinstance(body["reply"], str)
    assert len(body["reply"]) > 0
    assert "intent" in body
    assert isinstance(body["needs_human"], bool)


def test_wati_inbound_unknown_contact_contact_id_is_null():
    resp = client.post("/webhooks/wati", json={
        "waId": "+00000000000",
        "text": {"body": "Qui êtes-vous ?"},
    })
    assert resp.status_code == 202
    assert resp.json()["contact_id"] is None


def test_wati_inbound_known_contact_resolves_contact_id():
    # Create a contact via the systemeio webhook (flat payload — see normalizer)
    systemeio_payload = {
        "phone_number": "+22900000088",
        "first_name": "Kofi",
        "email": "kofi@test.com",
    }
    client.post("/webhooks/systemeio", json=systemeio_payload)

    # Now send inbound from that phone
    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000088",
        "text": {"body": "Quand commence le challenge ?"},
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["contact_id"] is not None
    assert body["contact_id"].startswith("ct_")


def test_wati_inbound_missing_phone_is_ignored():
    resp = client.post("/webhooks/wati", json={"text": {"body": "hello"}})
    assert resp.status_code == 202
    assert resp.json()["status"] == "ignored"


def test_wati_inbound_missing_text_is_ignored():
    resp = client.post("/webhooks/wati", json={"waId": "+22900000001"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "ignored"


def test_wati_inbound_flat_body_field_also_accepted():
    """Some Wati configurations send a flat 'body' field instead of 'text.body'."""
    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000077",
        "body": "Salut, comment ça marche ?",
    })
    assert resp.status_code == 202
    assert resp.json()["reply"]
