from fastapi.testclient import TestClient

from services.contacts.app.main import app as contacts_app
from services.consent.app.main import app as consent_app


def test_create_contact_then_check_eligibility():
    contact_client = TestClient(contacts_app)
    consent_client = TestClient(consent_app)

    response = contact_client.post("/contacts", json={
        "phone": "+22900000000",
        "first_name": "Ada",
        "source": "systemeio"
    })
    assert response.status_code == 201
    contact_id = response.json()["id"]

    optin = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "landing_page"
    })
    assert optin.status_code == 201

    eligibility = consent_client.get(f"/consents/{contact_id}/eligibility")
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True
