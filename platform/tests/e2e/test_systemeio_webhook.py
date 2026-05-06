from fastapi.testclient import TestClient

from services.integrations.app.main import app


def test_systemeio_webhook_is_normalized():
    client = TestClient(app)
    response = client.post("/webhooks/systemeio", json={
        "email": "ada@example.com",
        "phone_number": "+22900000000",
        "first_name": "Ada"
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["phone"] == "+22900000000"
