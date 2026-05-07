"""Tests for POST /scores/events — event recording, running total, auto-segment."""
from fastapi.testclient import TestClient

from services.scoring.app.main import app as scoring_app

client = TestClient(scoring_app)


def test_record_single_event_returns_score_and_segment():
    resp = client.post("/scores/events", json={
        "contact_id": "ct_ev_001",
        "event_type": "registered",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["contact_id"] == "ct_ev_001"
    assert body["event_type"] == "registered"
    assert body["points"] == 10
    assert body["total_score"] == 10
    assert body["segment"] == "froid"  # 10 ≤ 15


def test_multiple_events_accumulate_total():
    # registered=10, opened_message=5, clicked_link=10 → total=25 → tiede
    for event in ["registered", "opened_message", "clicked_link"]:
        resp = client.post("/scores/events", json={
            "contact_id": "ct_ev_002",
            "event_type": event,
        })
        assert resp.status_code == 201

    last = resp.json()
    assert last["total_score"] == 25
    assert last["segment"] == "tiede"  # 16..40


def test_high_engagement_reaches_tres_chaud():
    # registered=10, confirmed_live=30, paid_offer=50 → total=90 → tres_chaud
    for event in ["registered", "confirmed_live", "paid_offer"]:
        resp = client.post("/scores/events", json={
            "contact_id": "ct_ev_003",
            "event_type": event,
        })
        assert resp.status_code == 201

    last = resp.json()
    assert last["total_score"] == 90
    assert last["segment"] == "tres_chaud"  # > 75


def test_unknown_event_type_returns_400():
    resp = client.post("/scores/events", json={
        "contact_id": "ct_ev_bad",
        "event_type": "does_not_exist",
    })
    assert resp.status_code == 400
    assert "does_not_exist" in resp.json()["detail"]
