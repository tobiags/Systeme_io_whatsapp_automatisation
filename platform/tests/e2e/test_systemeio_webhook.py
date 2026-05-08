from fastapi.testclient import TestClient

from services.integrations.app.main import app

client = TestClient(app)


def test_systemeio_webhook_is_normalized():
    """Legacy flat format — still supported."""
    response = client.post("/webhooks/systemeio", json={
        "email": "ada@example.com",
        "phone_number": "+22900000000",
        "first_name": "Ada"
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["phone"] == "+22900000000"


def test_systemeio_real_webhook_format():
    """
    Real Systeme.io webhook payload (Context7 / developer.systeme.io docs).
    Phone and first_name are inside contact.fields array, not at top level.
    """
    response = client.post("/webhooks/systemeio", json={
        "contact": {
            "id": 12345,
            "email": "john@example.com",
            "registeredAt": "2024-01-01T00:00:00+00:00",
            "locale": "fr",
            "sourceURL": "https://webhook-optin.systeme.io/abc123",
            "unsubscribed": False,
            "bounced": False,
            "needsConfirmation": False,
            "fields": [
                {"fieldName": "first_name", "slug": "first_name", "value": "John"},
                {"fieldName": "last_name",  "slug": "last_name",  "value": "Doe"},
                {"fieldName": "phone_number", "slug": "phone_number", "value": "+22900000055"},
            ],
            "tags": [{"id": 1, "name": "challenge-fba"}],
        }
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["email"] == "john@example.com"
    assert body["payload"]["phone"] == "+22900000055"
    assert body["payload"]["first_name"] == "John"
    assert body["contact_id"] is not None


def test_systemeio_real_format_creates_contact_in_db():
    """Contact created from real Systeme.io format is findable by phone."""
    response = client.post("/webhooks/systemeio", json={
        "contact": {
            "id": 99999,
            "email": "kofi.real@example.com",
            "fields": [
                {"slug": "first_name",   "value": "Kofi"},
                {"slug": "phone_number", "value": "+22900000056"},
            ],
            "tags": [],
        }
    })
    assert response.status_code == 202
    body = response.json()
    assert body["contact_id"] is not None
    assert body["contact_id"].startswith("ct_")

    # Same phone again → upsert, not duplicate
    response2 = client.post("/webhooks/systemeio", json={
        "contact": {
            "id": 99999,
            "email": "kofi.real@example.com",
            "fields": [
                {"slug": "first_name",   "value": "Kofi Updated"},
                {"slug": "phone_number", "value": "+22900000056"},
            ],
            "tags": [],
        }
    })
    assert response2.status_code == 202
    # Same contact_id — upserted, not duplicated
    assert response2.json()["contact_id"] == body["contact_id"]
