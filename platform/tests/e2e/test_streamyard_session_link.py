from fastapi.testclient import TestClient

from services.integrations.app.main import app


def test_streamyard_link_is_bound_to_challenge_edition():
    client = TestClient(app)
    response = client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": "2026-05-07-eu",
        "region": "EU",
        "join_url": "https://streamyard.com/example"
    })
    assert response.status_code == 202
    assert response.json()["edition_key"] == "2026-05-07-eu"
    assert response.json()["join_url"] == "https://streamyard.com/example"
