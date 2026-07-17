"""Tests for smart enrollment skip logic.

The v7 journey keeps only one countdown step: COUNTDOWN_J1.
WELCOME is sent immediately by the Systeme.io webhook; contacts then wait at
COUNTDOWN_J1 until the day before the challenge, or jump to DAY_1 if the
challenge has already started.
"""
from services.campaigns.app.rules import compute_start_step


def test_more_than_one_day_starts_at_welcome():
    assert compute_start_step(2) == "WELCOME"
    assert compute_start_step(3) == "WELCOME"
    assert compute_start_step(6) == "WELCOME"
    assert compute_start_step(10) == "WELCOME"


def test_1_day_starts_at_countdown_j1():
    assert compute_start_step(1) == "COUNTDOWN_J1"


def test_0_days_starts_at_day1():
    assert compute_start_step(0) == "DAY_1"


def test_negative_days_starts_at_day1():
    assert compute_start_step(-1) == "DAY_1"
    assert compute_start_step(-5) == "DAY_1"


def test_enrollment_with_days_until_challenge_param_waits_at_welcome_before_j1():
    from fastapi.testclient import TestClient
    from services.campaigns.app.main import app

    client = TestClient(app)

    resp = client.post("/campaigns/enroll", json={
        "contact_id": "ct_skip_wait",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU",
        "days_until_challenge": 3,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["next_step"]["step_key"] == "WELCOME"
    assert body["next_step"]["template_key"] == "welcome_v1"


def test_enrollment_day0_starts_at_day1():
    from fastapi.testclient import TestClient
    from services.campaigns.app.main import app

    client = TestClient(app)

    resp = client.post("/campaigns/enroll", json={
        "contact_id": "ct_skip_day0",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU",
        "days_until_challenge": 0,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["next_step"]["step_key"] == "DAY_1"
    assert body["next_step"]["template_key"] == "live_day1_v1"
