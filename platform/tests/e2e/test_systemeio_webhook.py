from fastapi.testclient import TestClient

from services.integrations.app.main import app

client = TestClient(app)


def test_systemeio_webhook_is_normalized():
    """Legacy flat format remains supported."""
    response = client.post("/webhooks/systemeio", json={
        "email": "ada@example.com",
        "phone_number": "+22900000000",
        "first_name": "Ada",
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["phone"] == "22900000000"  # normalizer strips leading '+'


def test_systemeio_real_webhook_format():
    """Direct Systeme.io webhooks can send contact.fields as a list."""
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
                {"fieldName": "last_name", "slug": "last_name", "value": "Doe"},
                {"fieldName": "phone_number", "slug": "phone_number", "value": "+22900000055"},
            ],
            "tags": [{"id": 1, "name": "challenge-fba"}],
        }
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["email"] == "john@example.com"
    assert body["payload"]["phone"] == "22900000055"  # normalizer strips leading '+'
    assert body["payload"]["first_name"] == "John"
    assert body["contact_id"] is not None


def test_systemeio_real_format_creates_contact_in_db():
    """Direct Systeme.io contact payload upserts by phone."""
    response = client.post("/webhooks/systemeio", json={
        "contact": {
            "id": 99999,
            "email": "kofi.real@example.com",
            "fields": [
                {"slug": "first_name", "value": "Kofi"},
                {"slug": "phone_number", "value": "+22900000056"},
            ],
            "tags": [],
        }
    })
    assert response.status_code == 202
    body = response.json()
    assert body["contact_id"] is not None
    assert body["contact_id"].startswith("ct_")

    response2 = client.post("/webhooks/systemeio", json={
        "contact": {
            "id": 99999,
            "email": "kofi.real@example.com",
            "fields": [
                {"slug": "first_name", "value": "Kofi Updated"},
                {"slug": "phone_number", "value": "+22900000056"},
            ],
            "tags": [],
        }
    })
    assert response2.status_code == 202
    assert response2.json()["contact_id"] == body["contact_id"]


def test_systemeio_n8n_forwarded_optin_payload_is_normalized():
    """n8n forwards the Systeme.io payload under body.data.contact with dict fields."""
    response = client.post("/webhooks/systemeio", json={
        "headers": {
            "content-type": "application/json",
        },
        "body": {
            "type": "contact.optin.completed",
            "data": {
                "funnel_step": {
                    "id": 16107686,
                    "name": "Inscription US/CA",
                },
                "contact": {
                    "id": 423789441,
                    "email": "ecommercecentrale21@gmail.com",
                    "fields": {
                        "first_name": "Alban",
                        "phone_number": "447507135074",
                    },
                    "ip": "86.2.200.2",
                },
                "source_url": "https://www.ecommercecentrale.com/challenge-gratuit-fb-1",
            },
            "created_at": "2026-05-21T11:26:03+00:00",
        },
        "cohort": "US-CA",
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["email"] == "ecommercecentrale21@gmail.com"
    assert body["payload"]["phone"] == "447507135074"
    assert body["payload"]["first_name"] == "Alban"
    assert body["contact_id"] is not None
