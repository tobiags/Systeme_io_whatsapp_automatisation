from fastapi.testclient import TestClient

from services.api_gateway.app.main import app


def test_gateway_health_route():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_gateway_returns_service_list():
    client = TestClient(app)
    response = client.get("/services")
    assert response.status_code == 200
    services = response.json()["services"]
    assert "contacts" in services
    assert "campaigns" in services
    assert "messaging" in services
