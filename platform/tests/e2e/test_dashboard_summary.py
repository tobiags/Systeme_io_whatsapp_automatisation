"""Dashboard summary endpoint tests — validates all KPIs required by spec §11.4."""
from fastapi.testclient import TestClient

from services.dashboard_api.app.main import app
from shared.db.models import CampaignEnrollment, ChallengeEdition, Contact
from tests.conftest import _TestingSession

client = TestClient(app)


def test_dashboard_summary_returns_200():
    response = client.get("/dashboard/summary")
    assert response.status_code == 200


def test_dashboard_summary_has_all_required_kpis():
    """Spec §11.4: all required KPIs must be present."""
    body = client.get("/dashboard/summary").json()

    # Core KPIs
    assert "contacts_total" in body
    assert "messages_sent_total" in body
    assert "campaigns_active" in body
    assert "manual_followups" in body
    assert "conversion_rate" in body

    # Spec §11.4 — répartition EU/US-CA
    assert "contacts_by_cohort" in body
    assert isinstance(body["contacts_by_cohort"], dict)

    # Spec §11.4 — présence par jour
    assert "live_attendance_by_day" in body
    attendance = body["live_attendance_by_day"]
    assert "day1" in attendance
    assert "day2" in attendance
    assert "day3" in attendance

    # Spec §11.4 — FAQ dominantes
    assert "faq_counts" in body
    assert isinstance(body["faq_counts"], dict)

    # Spec §11.4 — objections financières
    assert "financial_objections_total" in body
    assert "financial_objections_by_type" in body
    assert isinstance(body["financial_objections_by_type"], dict)

    # Spec §11.4 — édition active (None when DB is empty, that's ok)
    assert "active_edition" in body

    # Spec §8 — segment distribution
    assert "contacts_by_segment" in body
    segments = body["contacts_by_segment"]
    for expected_segment in ("froid", "tiede", "chaud", "tres_chaud"):
        assert expected_segment in segments


def test_dashboard_numeric_fields_are_valid_types():
    body = client.get("/dashboard/summary").json()
    assert isinstance(body["contacts_total"], int)
    assert isinstance(body["messages_sent_total"], int)
    assert isinstance(body["campaigns_active"], int)
    assert isinstance(body["manual_followups"], int)
    assert isinstance(body["conversion_rate"], float)


def test_dashboard_conversion_rate_bounds():
    body = client.get("/dashboard/summary").json()
    rate = body["conversion_rate"]
    assert 0.0 <= rate <= 1.0


def test_dashboard_active_edition_ignores_invalid_operator_rows():
    db = _TestingSession()
    try:
        db.add(ChallengeEdition(
            id="ed_invalid",
            campaign_key="challenge-amazon-fba",
            edition_key="invalid-usca-import-2026-05-27",
            cohort="US-CA",
            edition_date="not-a-date",
        ))
        db.add(ChallengeEdition(
            id="ed_valid",
            campaign_key="challenge-amazon-fba",
            edition_key="2030-06-01-usca",
            cohort="US-CA",
            edition_date="2030-06-01",
        ))
        db.commit()
    finally:
        db.close()

    body = client.get("/dashboard/summary").json()
    assert body["active_edition"]["edition_key"] == "2030-06-01-usca"


def test_dashboard_separates_contacts_from_campaign_enrollments():
    db = _TestingSession()
    try:
        db.add(Contact(id="ct_dash_lead_only", phone="22911110000", first_name="Lead", source="test"))
        db.add(Contact(id="ct_dash_enrolled", phone="22911110001", first_name="Enrolled", source="test"))
        db.add(CampaignEnrollment(
            id="enr_dash_enrolled",
            contact_id="ct_dash_enrolled",
            campaign_key="challenge-amazon-fba",
            edition_key="2030-06-01-usca",
            current_step="WELCOME",
            cohort="US-CA",
        ))
        db.commit()
    finally:
        db.close()

    body = client.get("/dashboard/summary").json()
    assert body["contacts_total"] == 2
    assert body["enrollments_total"] == 1
    assert body["contacts_without_enrollment"] == 1
