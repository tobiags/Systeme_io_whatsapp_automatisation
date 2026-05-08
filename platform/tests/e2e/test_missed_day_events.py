"""Tests for day_missed tracking events (spec §5.3).

day1/2/3_live_missed are zero-point events used for audit and segmentation
tracking (absence does not penalise the score, but the event is recorded).
"""
from fastapi.testclient import TestClient

from services.scoring.app.main import app as scoring_app

client = TestClient(scoring_app)


def test_day1_live_missed_records_event_with_zero_points():
    resp = client.post("/scores/events", json={
        "contact_id": "ct_missed_1",
        "event_type": "day1_live_missed",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["points"] == 0
    assert body["event_type"] == "day1_live_missed"


def test_day2_live_missed_records_event_with_zero_points():
    resp = client.post("/scores/events", json={
        "contact_id": "ct_missed_2",
        "event_type": "day2_live_missed",
    })
    assert resp.status_code == 201
    assert resp.json()["points"] == 0


def test_day3_live_missed_records_event_with_zero_points():
    resp = client.post("/scores/events", json={
        "contact_id": "ct_missed_3",
        "event_type": "day3_live_missed",
    })
    assert resp.status_code == 201
    assert resp.json()["points"] == 0


def test_missed_event_does_not_change_segment():
    """Recording missed events must not alter score or segment."""
    # First give the contact some points
    client.post("/scores/events", json={"contact_id": "ct_missed_seg", "event_type": "registered"})
    client.post("/scores/events", json={"contact_id": "ct_missed_seg", "event_type": "day1_live_joined"})

    before_resp = client.post("/scores/events", json={
        "contact_id": "ct_missed_seg", "event_type": "day2_live_joined"
    })
    score_before = before_resp.json()["total_score"]  # 10 + 30 + 25 = 65

    after_resp = client.post("/scores/events", json={
        "contact_id": "ct_missed_seg", "event_type": "day3_live_missed"
    })
    assert after_resp.json()["total_score"] == score_before  # unchanged


def test_combined_joined_and_missed_events():
    """A contact can have both joined and missed events in their history."""
    for evt in ["registered", "day1_live_joined", "day2_live_missed"]:
        resp = client.post("/scores/events", json={
            "contact_id": "ct_mixed_events",
            "event_type": evt,
        })
        assert resp.status_code == 201

    # Final score: 10 (registered) + 30 (day1_joined) + 0 (day2_missed) = 40
    assert resp.json()["total_score"] == 40
    assert resp.json()["segment"] == "tiede"
