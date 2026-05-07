"""Tests for expanded scoring rules — day1/2/3 live, group join, offer interest."""
from fastapi.testclient import TestClient

from services.scoring.app.main import app as scoring_app

client = TestClient(scoring_app)


def test_day1_live_joined_scores_30():
    resp = client.post("/scores/events", json={"contact_id": "ct_d1", "event_type": "day1_live_joined"})
    assert resp.status_code == 201
    assert resp.json()["points"] == 30
    assert resp.json()["total_score"] == 30


def test_day2_live_joined_scores_25():
    resp = client.post("/scores/events", json={"contact_id": "ct_d2", "event_type": "day2_live_joined"})
    assert resp.status_code == 201
    assert resp.json()["points"] == 25


def test_day3_live_joined_scores_25():
    resp = client.post("/scores/events", json={"contact_id": "ct_d3", "event_type": "day3_live_joined"})
    assert resp.status_code == 201
    assert resp.json()["points"] == 25


def test_group_whatsapp_joined_scores_15():
    resp = client.post("/scores/events", json={"contact_id": "ct_grp", "event_type": "group_whatsapp_joined"})
    assert resp.status_code == 201
    assert resp.json()["points"] == 15


def test_full_attendance_all_3_days_reaches_tres_chaud():
    # registered=10 + group=15 + day1=30 + day2=25 + day3=25 = 105 → tres_chaud
    contact = "ct_full"
    for event in ["registered", "group_whatsapp_joined", "day1_live_joined", "day2_live_joined", "day3_live_joined"]:
        resp = client.post("/scores/events", json={"contact_id": contact, "event_type": event})
        assert resp.status_code == 201
    assert resp.json()["total_score"] == 105
    assert resp.json()["segment"] == "tres_chaud"


def test_offer_interest_detected_scores_20():
    resp = client.post("/scores/events", json={"contact_id": "ct_oi", "event_type": "offer_interest_detected"})
    assert resp.status_code == 201
    assert resp.json()["points"] == 20


def test_conversion_intent_detected_scores_35():
    resp = client.post("/scores/events", json={"contact_id": "ct_ci", "event_type": "conversion_intent_detected"})
    assert resp.status_code == 201
    assert resp.json()["points"] == 35
