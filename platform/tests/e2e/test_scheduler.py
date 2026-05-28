"""Tests for the campaign edition scheduler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.campaigns.app import tasks as campaign_tasks
from services.campaigns.app.scheduler import schedule_edition


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_result(task_id: str = "fake-id"):
    m = MagicMock()
    m.id = task_id
    return m


def _patch_all_tasks():
    """Patch every timed dispatch task so no broker is needed in tests."""
    return [
        patch.object(campaign_tasks.dispatch_h2,       "apply_async", return_value=_fake_result("id_h2")),
        patch.object(campaign_tasks.dispatch_h10,      "apply_async", return_value=_fake_result("id_h10")),
        patch.object(campaign_tasks.dispatch_h_plus_5, "apply_async", return_value=_fake_result("id_h_plus_5")),
        patch.object(campaign_tasks.dispatch_h_plus_2, "apply_async", return_value=_fake_result("id_h_plus_2")),
    ]


def _future_date(days: int = 90) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_schedule_edition_returns_10_tasks_for_future_edition():
    """3 tasks × 3 days + dispatch_h_plus_2 × 1 day = 10 for an entirely-future edition."""
    patchers = _patch_all_tasks()
    for p in patchers:
        p.start()

    try:
        date = _future_date()
        scheduled = schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key=f"{date}-eu",
            cohort="EU",
            edition_date=date,
            streamyard_url="https://streamyard.com/test",
        )
    finally:
        for p in patchers:
            p.stop()

    assert len(scheduled) == 10, f"Expected 10 tasks, got {len(scheduled)}"


def test_schedule_edition_correct_day_numbers():
    """Days 1, 2, and 3 must all appear in the scheduled descriptors."""
    patchers = _patch_all_tasks()
    for p in patchers:
        p.start()

    try:
        date = _future_date()
        scheduled = schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key=f"{date}-eu",
            cohort="EU",
            edition_date=date,
        )
    finally:
        for p in patchers:
            p.stop()

    assert {e["day"] for e in scheduled} == {1, 2, 3}


def test_schedule_edition_correct_timings():
    """All V3 timing suffixes must be scheduled."""
    patchers = _patch_all_tasks()
    for p in patchers:
        p.start()

    try:
        date = _future_date()
        scheduled = schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key=f"{date}-eu",
            cohort="EU",
            edition_date=date,
        )
    finally:
        for p in patchers:
            p.stop()

    assert {e["task"] for e in scheduled} == {
        "dispatch_h2", "dispatch_h10", "dispatch_h_plus_5", "dispatch_h_plus_2"
    }


def test_schedule_edition_can_limit_scheduling_to_one_live_day():
    """The ops page must schedule only the live day the client just saved."""
    patchers = _patch_all_tasks()
    for p in patchers:
        p.start()

    try:
        date = _future_date()
        scheduled = schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key=f"{date}-usca",
            cohort="US-CA",
            edition_date=date,
            day_number=1,
        )
    finally:
        for p in patchers:
            p.stop()

    assert {entry["day"] for entry in scheduled} == {1}
    assert {entry["task"] for entry in scheduled} == {
        "dispatch_h2",
        "dispatch_h10",
        "dispatch_h_plus_5",
    }


def test_schedule_edition_past_edition_skips_all():
    """An edition entirely in the past should produce 0 scheduled tasks."""
    patchers = _patch_all_tasks()
    for p in patchers:
        p.start()

    try:
        scheduled = schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key="2020-01-01-eu",
            cohort="EU",
            edition_date="2020-01-01",
        )
    finally:
        for p in patchers:
            p.stop()

    assert scheduled == []


def test_schedule_edition_eta_ordering():
    """h2 < h10 < h_plus_5 for each day."""
    # Capture ETAs per timing for day 1.
    captured: dict[str, list[datetime]] = {"h2": [], "h10": [], "h_plus_5": []}

    def _capture(name):
        def _side_effect(**kwargs):
            eta = kwargs.get("eta")
            if eta:
                captured[name].append(eta)
            return _fake_result()
        return _side_effect

    patchers = [
        patch.object(campaign_tasks.dispatch_h2,       "apply_async", side_effect=_capture("h2")),
        patch.object(campaign_tasks.dispatch_h10,      "apply_async", side_effect=_capture("h10")),
        patch.object(campaign_tasks.dispatch_h_plus_5, "apply_async", side_effect=_capture("h_plus_5")),
        patch.object(campaign_tasks.dispatch_h_plus_2, "apply_async", return_value=_fake_result()),
    ]
    for p in patchers:
        p.start()

    try:
        date = _future_date()
        schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key=f"{date}-eu",
            cohort="EU",
            edition_date=date,
        )
    finally:
        for p in patchers:
            p.stop()

    # 3 ETAs per timing (one per day).
    for name in ("h2", "h10", "h_plus_5"):
        assert len(captured[name]) == 3, f"Expected 3 ETAs for {name}, got {len(captured[name])}"

    # For day 1 (index 0): h2 < h10 < h_plus_5.
    h2, h10, h_plus_5 = (captured[t][0] for t in ("h2", "h10", "h_plus_5"))
    assert h2 < h10 < h_plus_5

    # H-2 to H-10 gap should be ~110 min.
    diff = h10 - h2
    assert timedelta(minutes=109) <= diff <= timedelta(minutes=111)

    # H-10 to H+5 gap should be ~15 min.
    diff2 = h_plus_5 - h10
    assert timedelta(minutes=14) <= diff2 <= timedelta(minutes=16)


def test_schedule_edition_live_reminders_resolve_streamyard_url_at_dispatch_time():
    """Timed tasks should resolve the per-day URL from the edition when they run."""
    captured: dict[str, list[dict]] = {"h2": [], "h10": [], "h_plus_5": []}

    def _capture(name):
        def _side_effect(**kwargs):
            captured[name].append(kwargs.get("kwargs", {}))
            return _fake_result()
        return _side_effect

    patchers = _patch_all_tasks()
    patchers[0] = patch.object(campaign_tasks.dispatch_h2, "apply_async", side_effect=_capture("h2"))
    patchers[1] = patch.object(campaign_tasks.dispatch_h10, "apply_async", side_effect=_capture("h10"))
    patchers[2] = patch.object(campaign_tasks.dispatch_h_plus_5, "apply_async", side_effect=_capture("h_plus_5"))

    for p in patchers:
        p.start()

    try:
        date = _future_date()
        sy_url = "https://streamyard.com/abc"
        schedule_edition(
            campaign_key="challenge-amazon-fba",
            edition_key=f"{date}-eu",
            cohort="EU",
            edition_date=date,
            streamyard_url=sy_url,
        )
    finally:
        for p in patchers:
            p.stop()

    for name in ("h2", "h10", "h_plus_5"):
        assert len(captured[name]) == 3
        for kw in captured[name]:
            assert kw.get("streamyard_url") == ""
