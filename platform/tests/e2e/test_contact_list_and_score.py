"""Tests for GET /contacts (list) and GET /contacts/{id}/score."""
from fastapi.testclient import TestClient

from services.contacts.app.main import app as contacts_app
from services.scoring.app.main import app as scoring_app

contacts_client = TestClient(contacts_app)
scoring_client = TestClient(scoring_app)


def test_list_contacts_empty_initially():
    resp = contacts_client.get("/contacts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_contacts_returns_created_contacts():
    contacts_client.post("/contacts", json={"phone": "+33100000001", "first_name": "Alice", "source": "test"})
    contacts_client.post("/contacts", json={"phone": "+33100000002", "first_name": "Bob", "source": "test"})

    resp = contacts_client.get("/contacts")
    assert resp.status_code == 200
    phones = [c["phone"] for c in resp.json()]
    assert "+33100000001" in phones
    assert "+33100000002" in phones


def test_get_contact_score_zero_before_any_event():
    # Create a contact
    create = contacts_client.post("/contacts", json={"phone": "+33199999901", "source": "test"})
    contact_id = create.json()["id"]

    resp = contacts_client.get(f"/contacts/{contact_id}/score")
    assert resp.status_code == 200
    assert resp.json()["total_score"] == 0
    assert resp.json()["contact_id"] == contact_id


def test_get_contact_score_after_events():
    # Create contact
    create = contacts_client.post("/contacts", json={"phone": "+33199999902", "source": "test"})
    contact_id = create.json()["id"]

    # Record events via scoring service
    scoring_client.post("/scores/events", json={"contact_id": contact_id, "event_type": "registered"})
    scoring_client.post("/scores/events", json={"contact_id": contact_id, "event_type": "clicked_link"})

    # Check through contacts service (same DB via conftest override)
    resp = contacts_client.get(f"/contacts/{contact_id}/score")
    assert resp.status_code == 200
    assert resp.json()["total_score"] == 20  # registered=10, clicked_link=10
