"""Tests for POST /webhooks/wati — inbound WhatsApp message processing."""
from fastapi.testclient import TestClient

from services.contacts.app.main import app as contacts_app
from services.integrations.app.main import app as integrations_app
from services.messaging.app.main import app as messaging_app

client = TestClient(integrations_app)
contacts_client = TestClient(contacts_app)
messaging_client = TestClient(messaging_app)

# Wati v3 real webhook payload — text is a plain string (not a nested object)
WATI_PAYLOAD_V3 = {
    "waId": "+22900000099",
    "text": "Bonjour, c'est quoi le challenge ?",
    "type": "text",
    "senderName": "Test User",
    "eventType": "message",
}

# Backwards-compat: some tests/integrations send {"text": {"body": "..."}}
WATI_PAYLOAD_LEGACY = {
    "waId": "+22900000099",
    "text": {"body": "Bonjour, c'est quoi le challenge ?"},
}

# Keep original name pointing to real format
WATI_PAYLOAD = WATI_PAYLOAD_V3


def test_wati_inbound_returns_reply():
    resp = client.post("/webhooks/wati", json=WATI_PAYLOAD)
    assert resp.status_code == 202
    body = resp.json()
    assert body["phone"] == "+22900000099"
    assert isinstance(body["reply"], str)
    assert len(body["reply"]) > 0
    assert "intent" in body
    assert isinstance(body["needs_human"], bool)


def test_wati_inbound_v3_plain_text_string():
    """Wati v3 sends text as a plain string — must be parsed correctly."""
    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000098",
        "text": "quand ca commence ?",
        "type": "text",
        "eventType": "message",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["phone"] == "+22900000098"
    assert body["intent"] == "faq_start_time"
    assert isinstance(body["reply"], str) and len(body["reply"]) > 0


def test_wati_inbound_legacy_nested_text_still_works():
    """Legacy format with text as {body: ...} still accepted."""
    resp = client.post("/webhooks/wati", json=WATI_PAYLOAD_LEGACY)
    assert resp.status_code == 202
    assert resp.json()["reply"]


def test_wati_inbound_unknown_contact_contact_id_is_null():
    resp = client.post("/webhooks/wati", json={
        "waId": "+00000000000",
        "text": "Qui êtes-vous ?",
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

    # Now send inbound from that phone (Wati v3 plain-string format)
    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000088",
        "text": "Quand commence le challenge ?",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["contact_id"] is not None
    assert body["contact_id"].startswith("ct_")


def test_wati_inbound_missing_phone_is_ignored():
    resp = client.post("/webhooks/wati", json={"text": "hello"})
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


def test_wati_inbound_known_contact_records_reply_and_question_signals():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000066",
        "first_name": "Ama",
        "email": "ama@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000066",
        "text": "Quel est le principal blocage pour commencer ?",
        "eventType": "messageReceived",
    })
    assert resp.status_code == 202
    contact_id = resp.json()["contact_id"]
    assert contact_id is not None

    score = contacts_client.get(f"/contacts/{contact_id}/score")
    assert score.status_code == 200
    assert score.json()["total_score"] == 30


def test_wati_read_receipt_scores_opened_message():
    create = contacts_client.post("/contacts", json={
        "phone": "+22900000055",
        "first_name": "Kojo",
        "source": "test",
    })
    contact_id = create.json()["id"]

    sent = messaging_client.post("/messages/send", json={
        "contact_id": contact_id,
        "template_key": "welcome",
        "variables": {"first_name": "Kojo"},
    })
    message_id = sent.json()["message_id"]

    resp = client.post("/webhooks/wati", json={
        "eventType": "sentMessageREAD_v2",
        "localMessageId": message_id,
    })
    assert resp.status_code == 202

    score = contacts_client.get(f"/contacts/{contact_id}/score")
    assert score.status_code == 200
    assert score.json()["total_score"] == 5
