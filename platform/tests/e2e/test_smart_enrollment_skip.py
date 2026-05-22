"""Tests for smart enrollment skip logic.

Late registrants skip past already-elapsed countdown steps based on the
`days_until_challenge` parameter passed at enrollment time.

Logic (compute_start_step):
  days >= 7  → WELCOME (full sequence)
  days == 6  → WELCOME (normal J-7 day, J6 countdown tomorrow)
  days == 5  → COUNTDOWN_J5 (WELCOME sent, then jump to J5)
  ...
  days == 1  → COUNTDOWN_J1
  days == 0  → DAY_1 (challenge starts today, skip all countdowns)
  days < 0   → DAY_1
"""
from services.campaigns.app.rules import compute_start_step


def test_7_or_more_days_starts_at_welcome():
    assert compute_start_step(7) == "WELCOME"
    assert compute_start_step(10) == "WELCOME"
    assert compute_start_step(100) == "WELCOME"


def test_6_days_skips_to_countdown_j6():
    """6 days left → skips WELCOME, starts directly at COUNTDOWN_J6.

    WELCOME is delivered immediately via the Systeme.io webhook at registration.
    The broadcast sequence for a J-6 registrant picks up at COUNTDOWN_J6.
    """
    assert compute_start_step(6) == "COUNTDOWN_J6"


def test_5_days_skips_to_countdown_j5():
    assert compute_start_step(5) == "COUNTDOWN_J5"


def test_4_days_skips_to_countdown_j4():
    assert compute_start_step(4) == "COUNTDOWN_J4"


def test_3_days_skips_to_countdown_j3():
    assert compute_start_step(3) == "COUNTDOWN_J3"


def test_2_days_skips_to_countdown_j2():
    assert compute_start_step(2) == "COUNTDOWN_J2"


def test_1_day_skips_to_countdown_j1():
    assert compute_start_step(1) == "COUNTDOWN_J1"


def test_0_days_starts_at_day1():
    """Challenge starts today — skip all countdowns."""
    assert compute_start_step(0) == "DAY_1"


def test_negative_days_starts_at_day1():
    """Challenge already started — also routes to DAY_1."""
    assert compute_start_step(-1) == "DAY_1"
    assert compute_start_step(-5) == "DAY_1"


def test_enrollment_with_days_until_challenge_param():
    """Enrollment endpoint accepts days_until_challenge and sets correct step."""
    from fastapi.testclient import TestClient
    from services.campaigns.app.main import app

    client = TestClient(app)

    resp = client.post("/campaigns/enroll", json={
        "contact_id": "ct_skip_j3",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU",
        "days_until_challenge": 3,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["next_step"]["step_key"] == "COUNTDOWN_J3"
    assert body["next_step"]["template_key"] == "countdown_j3"


def test_enrollment_day0_starts_at_day1():
    """Enrollment with days_until_challenge=0 places contact at DAY_1."""
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
    assert body["next_step"]["template_key"] == "live_day1"
