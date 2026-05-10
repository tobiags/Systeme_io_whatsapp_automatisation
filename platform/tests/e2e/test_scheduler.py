"""Tests for the campaign edition scheduler.

Celery apply_async is mocked via patch.object so no Redis is needed in CI.
The _OFFSETS list in scheduler.py holds direct task references, so we must
patch apply_async on the task objects themselves (not on the module name).
"""
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
    """Return context managers that patch apply_async on all 5 dispatch tasks.

    Includes dispatch_h_plus_2 (Day-3 only) so no Redis connection is attempted
    during tests.
    """
    return [
        patch.object(campaign_tasks.dispatch_h6,       "apply_async", return_value=_fake_result("id_h6")),
        patch.object(campaign_tasks.dispatch_h45,      "apply_async", return_value=_fake_result("id_h45")),
        patch.object(campaign_tasks.dispatch_h10,      "apply_async", return_value=_fake_result("id_h10")),
        patch.object(campaign_tasks.dispatch_recap,    "apply_async", return_value=_fake_result("id_recap")),
        patch.object(campaign_tasks.dispatch_h_plus_2, "apply_async", return_value=_fake_result("id_h_plus_2")),
    ]


def _future_date(days: int = 90) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_schedule_edition_returns_13_tasks_for_future_edition():
    """4 tasks × 3 days + dispatch_h_plus_2 × 1 day = 13 for an entirely-future edition."""
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

    assert len(scheduled) == 13, f"Expected 13 tasks, got {len(scheduled)}"


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
    """All 4 timing suffixes must be scheduled."""
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
        "dispatch_h6", "dispatch_h45", "dispatch_h10", "dispatch_recap", "dispatch_h_plus_2"
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
    """h6 < h45 < h10 < recap for each day."""
    # Capture ETAs per timing for day 1.
    captured: dict[str, list[datetime]] = {"h6": [], "h45": [], "h10": [], "recap": []}

    def _capture(name):
        def _side_effect(**kwargs):
            eta = kwargs.get("eta")
            if eta:
                captured[name].append(eta)
            return _fake_result()
        return _side_effect

    patchers = [
        patch.object(campaign_tasks.dispatch_h6,       "apply_async", side_effect=_capture("h6")),
        patch.object(campaign_tasks.dispatch_h45,      "apply_async", side_effect=_capture("h45")),
        patch.object(campaign_tasks.dispatch_h10,      "apply_async", side_effect=_capture("h10")),
        patch.object(campaign_tasks.dispatch_recap,    "apply_async", side_effect=_capture("recap")),
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
    for name in ("h6", "h45", "h10", "recap"):
        assert len(captured[name]) == 3, f"Expected 3 ETAs for {name}, got {len(captured[name])}"

    # For day 1 (index 0): h6 < h45 < h10 < recap.
    h6, h45, h10, rec = (captured[t][0] for t in ("h6", "h45", "h10", "recap"))
    assert h6 < h45 < h10 < rec

    # H-6 to H-45 gap should be ~5h15m (315 min ± 2 min tolerance).
    diff = h45 - h6
    assert timedelta(minutes=313) <= diff <= timedelta(minutes=317)

    # H-45 to H-10 gap should be ~35 min.
    diff2 = h10 - h45
    assert timedelta(minutes=34) <= diff2 <= timedelta(minutes=36)


def test_schedule_edition_h45_carries_streamyard_url():
    """Only dispatch_h45 should receive the streamyard_url kwarg."""
    h45_kwargs: list[dict] = []

    def _capture_h45(**kwargs):
        h45_kwargs.append(kwargs.get("kwargs", {}))
        return _fake_result()

    patchers = _patch_all_tasks()
    # Override the h45 patcher with our capturing version.
    patchers[1] = patch.object(campaign_tasks.dispatch_h45, "apply_async", side_effect=_capture_h45)

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

    # Called 3 times (once per day), each with the streamyard_url.
    assert len(h45_kwargs) == 3
    for kw in h45_kwargs:
        assert kw.get("streamyard_url") == sy_url
