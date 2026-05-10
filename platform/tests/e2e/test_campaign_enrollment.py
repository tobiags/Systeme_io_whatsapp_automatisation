from fastapi.testclient import TestClient

from services.campaigns.app.main import app


def test_enroll_contact_into_journey_creates_first_scheduled_step():
    client = TestClient(app)
    response = client.post("/campaigns/enroll", json={
        "contact_id": "ct_123",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU"
    })
    assert response.status_code == 201
    body = response.json()
    assert body["campaign_key"] == "challenge-amazon-fba"
    assert body["cohort"] == "EU"
    assert body["next_step"]["step_key"] == "WELCOME"
    assert body["next_step"]["template_key"] == "welcome"
    assert body["live_timezone"] == "Europe"
