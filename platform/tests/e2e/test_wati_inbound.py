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
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == "+22900000099"
    assert isinstance(body["reply"], str)
    assert len(body["reply"]) > 0
    assert "intent" in body
    assert isinstance(body["needs_human"], bool)
    assert body["delivery"]["status"] == "queued"


def test_wati_inbound_v3_plain_text_string():
    """Wati v3 sends text as a plain string — must be parsed correctly."""
    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000098",
        "text": "quand ca commence ?",
        "type": "text",
        "eventType": "message",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == "+22900000098"
    assert body["intent"] == "faq_start_time"
    assert isinstance(body["reply"], str) and len(body["reply"]) > 0


def test_wati_inbound_legacy_nested_text_still_works():
    """Legacy format with text as {body: ...} still accepted."""
    resp = client.post("/webhooks/wati", json=WATI_PAYLOAD_LEGACY)
    assert resp.status_code == 200
    assert resp.json()["reply"]


def test_wati_inbound_unknown_contact_contact_id_is_null():
    resp = client.post("/webhooks/wati", json={
        "waId": "+00000000000",
        "text": "Qui êtes-vous ?",
    })
    assert resp.status_code == 200
    assert resp.json()["contact_id"] is None
    assert resp.json()["delivery"]["status"] == "awaiting_human"
    assert resp.json()["needs_human"] is True


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
    assert resp.status_code == 200
    body = resp.json()
    assert body["contact_id"] is not None
    assert body["contact_id"].startswith("ct_")


def test_wati_inbound_matches_contact_even_if_plus_prefix_differs():
    client.post("/webhooks/systemeio", json={
        "phone_number": "22900000087",
        "first_name": "Nadia",
        "email": "nadia@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000087",
        "text": "Je pars de zero",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["contact_id"] is not None
    assert body["intent"] == "beginner_profile"


def test_wati_inbound_missing_phone_is_ignored():
    resp = client.post("/webhooks/wati", json={"text": "hello"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_wati_inbound_missing_text_is_ignored():
    resp = client.post("/webhooks/wati", json={"waId": "+22900000001"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_wati_inbound_flat_body_field_also_accepted():
    """Some Wati configurations send a flat 'body' field instead of 'text.body'."""
    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000077",
        "body": "Salut, comment ça marche ?",
    })
    assert resp.status_code == 200
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
    assert resp.status_code == 200
    contact_id = resp.json()["contact_id"]
    assert contact_id is not None

    score = contacts_client.get(f"/contacts/{contact_id}/score")
    assert score.status_code == 200
    assert score.json()["total_score"] == 30
    assert resp.json()["delivery"]["status"] == "awaiting_human"
    assert resp.json()["needs_human"] is True
    assert resp.json()["delivery"]["message_id"] is None


def test_wati_inbound_known_contact_persists_ai_session_reply_message():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000065",
        "first_name": "Awa",
        "email": "awa@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000065",
        "text": "Quand est-ce que cela commence ?",
        "eventType": "messageReceived",
    })
    assert resp.status_code == 200
    delivery = resp.json()["delivery"]
    assert delivery["status"] == "queued"
    message_id = delivery["message_id"]
    assert message_id is not None

    from shared.db.models import Message
    from tests.conftest import _TestingSession

    db = _TestingSession()
    try:
        row = db.query(Message).filter(Message.id == message_id).first()
        assert row is not None
        assert row.template_key == "ai_session_reply"
        assert row.variables["text"]
        assert row.provider in {"mock", "wati", "360dialog"}
    finally:
        db.close()


def test_wati_inbound_beginner_profile_message_returns_specific_reply():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000064",
        "first_name": "Prince",
        "email": "prince@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000064",
        "text": "Je pars de zero",
        "eventType": "messageReceived",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "beginner_profile"
    assert body["delivery"]["status"] == "queued"
    assert "pas a pas" in body["reply"].lower()
    assert "?" not in body["reply"]


def test_wati_inbound_handles_de_zero_variant():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000063",
        "first_name": "Joel",
        "email": "joel@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000063",
        "text": "De 0",
        "eventType": "messageReceived",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "beginner_profile"


def test_wati_inbound_reprompts_from_welcome_context_when_message_is_generic():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000062",
        "first_name": "Mira",
        "email": "mira@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000062",
        "text": "Bonjour",
        "eventType": "messageReceived",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "welcome_followup_reprompt"
    assert "partez de zero" in body["reply"].lower()


def test_wati_inbound_ignores_recent_duplicate_same_message():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000061",
        "first_name": "Eli",
        "email": "eli@test.com",
    })

    first = client.post("/webhooks/wati", json={
        "waId": "+22900000061",
        "text": "Je pars de zero",
        "eventType": "messageReceived",
    })
    assert first.status_code == 200
    assert first.json()["delivery"]["status"] == "queued"

    second = client.post("/webhooks/wati", json={
        "waId": "+22900000061",
        "text": "Je pars de zero",
        "eventType": "messageReceived",
    })
    assert second.status_code == 200
    assert second.json()["delivery"]["status"] == "duplicate_ignored"
    assert second.json()["reply"] == first.json()["reply"]


def test_wati_inbound_continues_beginner_conversation_after_followup_answer():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000060",
        "first_name": "Noe",
        "email": "noe@test.com",
    })

    first = client.post("/webhooks/wati", json={
        "waId": "+22900000060",
        "text": "Je pars de zero",
        "eventType": "messageReceived",
    })
    assert first.status_code == 200
    assert first.json()["intent"] == "beginner_profile"

    second = client.post("/webhooks/wati", json={
        "waId": "+22900000060",
        "text": "Tous les produits",
        "eventType": "messageReceived",
    })
    assert second.status_code == 200
    body = second.json()
    assert body["intent"] == "beginner_profile_followup"
    assert "produit simple" in body["reply"].lower()
    assert "?" not in body["reply"]


def test_wati_inbound_unknown_message_prefers_human_queue_over_robotic_fallback():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000059",
        "first_name": "Lina",
        "email": "lina@test.com",
    })

    resp = client.post("/webhooks/wati", json={
        "waId": "+22900000059",
        "text": "Mon cas est un peu particulier",
        "eventType": "messageReceived",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "default"
    assert body["needs_human"] is True
    assert body["reply"] == ""
    assert body["delivery"]["status"] == "awaiting_human"


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
    provider_message_id = sent.json()["provider_message_id"]

    resp = client.post("/webhooks/wati", json={
        "eventType": "sentMessageREAD_v2",
        "localMessageId": provider_message_id,
    })
    assert resp.status_code == 200

    score = contacts_client.get(f"/contacts/{contact_id}/score")
    assert score.status_code == 200
    assert score.json()["total_score"] == 5


def test_wati_delivered_receipt_updates_message_status():
    create = contacts_client.post("/contacts", json={
        "phone": "+22900000054",
        "first_name": "Esi",
        "source": "test",
    })
    contact_id = create.json()["id"]

    sent = messaging_client.post("/messages/send", json={
        "contact_id": contact_id,
        "template_key": "welcome",
        "variables": {"first_name": "Esi"},
    })
    provider_message_id = sent.json()["provider_message_id"]

    resp = client.post("/webhooks/wati", json={
        "eventType": "sentMessageDELIVERED_v2",
        "localMessageId": provider_message_id,
    })
    assert resp.status_code == 200

    from shared.db.models import Message
    from tests.conftest import _TestingSession

    db = _TestingSession()
    try:
        row = db.query(Message).filter(Message.provider_message_id == provider_message_id).first()
        assert row is not None
        assert row.status == "delivered"
    finally:
        db.close()
