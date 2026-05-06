from fastapi.testclient import TestClient

from services.messaging.app.main import app


def test_send_message_returns_delivery_record():
    client = TestClient(app)
    response = client.post("/messages/send", json={
        "contact_id": "ct_123",
        "template_key": "welcome_j7",
        "variables": {"first_name": "Ada"}
    })
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["provider"] in {"wati", "360dialog", "mock"}
