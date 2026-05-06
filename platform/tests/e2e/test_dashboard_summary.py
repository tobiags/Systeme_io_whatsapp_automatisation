from fastapi.testclient import TestClient

from services.dashboard_api.app.main import app


def test_dashboard_summary_endpoint_returns_kpis():
    client = TestClient(app)
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    body = response.json()
    assert "contacts_total" in body
    assert "campaigns_active" in body
    assert "manual_followups" in body
