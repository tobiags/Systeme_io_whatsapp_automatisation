"""Tests for POST /webhooks/engagement — generic behavior signal ingestion."""
from fastapi.testclient import TestClient

from services.contacts.app.main import app as contacts_app
from services.integrations.app.main import app as integrations_app

integrations_client = TestClient(integrations_app)
contacts_client = TestClient(contacts_app)


def _create_contact(phone: str, first_name: str = "Signal") -> str:
    resp = contacts_client.post("/contacts", json={
        "phone": phone,
        "first_name": first_name,
        "source": "test",
    })
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def test_engagement_webhook_normalizes_group_join_alias():
    contact_id = _create_contact("33810000001")

    resp = integrations_client.post("/webhooks/engagement", json={
        "phone": "33810000001",
        "event_type": "group_joined",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "recorded"
    assert body["contact_id"] == contact_id
    assert body["event_type"] == "group_whatsapp_joined"
    assert body["points"] == 15
    assert body["segment"] == "froid"


def test_engagement_webhook_normalizes_streamyard_click_alias():
    contact_id = _create_contact("33810000002")

    resp = integrations_client.post("/webhooks/engagement", json={
        "contact_id": contact_id,
        "event_type": "streamyard_clicked",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["event_type"] == "streamyard_link_clicked"
    assert body["points"] == 10
    assert body["contact_id"] == contact_id


def test_engagement_webhook_unknown_contact_is_ignored():
    resp = integrations_client.post("/webhooks/engagement", json={
        "phone": "33819999999",
        "event_type": "group_joined",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "ignored"
    assert body["reason"] == "contact_not_found"


def test_engagement_webhook_invalid_event_rejected():
    _create_contact("33810000003")

    resp = integrations_client.post("/webhooks/engagement", json={
        "phone": "33810000003",
        "event_type": "totally_unknown_signal",
    })
    assert resp.status_code == 400
    assert "totally_unknown_signal" in resp.json()["detail"]


def test_engagement_webhook_poll_answer_updates_score_log():
    contact_id = _create_contact("33810000004")

    resp = integrations_client.post("/webhooks/engagement", json={
        "contact_id": contact_id,
        "event_type": "poll_answered",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "recorded"
    assert body["event_type"] == "poll_answered"
    assert body["points"] == 10

    score = contacts_client.get(f"/contacts/{contact_id}/score")
    assert score.status_code == 200
    assert score.json()["total_score"] == body["total_score"]
