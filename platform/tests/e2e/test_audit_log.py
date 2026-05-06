from fastapi.testclient import TestClient

from services.observability.app.main import app


def test_audit_log_accepts_event():
    client = TestClient(app)
    response = client.post("/audit/events", json={
        "name": "message.sent",
        "aggregate_id": "ct_123",
        "payload": {"template_key": "welcome_j7"}
    })
    assert response.status_code == 201
    assert response.json()["name"] == "message.sent"


def test_audit_log_lists_events():
    client = TestClient(app)
    client.post("/audit/events", json={
        "name": "contact.created",
        "aggregate_id": "ct_456",
        "payload": {"source": "systemeio"}
    })
    response = client.get("/audit/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
