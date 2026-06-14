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


def _patch_broadcast():
    """Patch dispatch_broadcast so no broker is needed in tests."""
    return [
        patch.object(campaign_tasks.dispatch_broadcast, "apply_async", return_value=_fake_result("id_broadcast")),
    ]


def _future_date(days: int = 90) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_schedule_edition_returns_6_tasks_for_future_edition():
    """3 broadcast ETA tasks + 3 h10 heartbeat entries = 6 for an entirely-future edition."""
    patchers = _patch_broadcast()
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

    assert len(scheduled) == 6, f"Expected 6 tasks, got {len(scheduled)}"


def test_schedule_edition_correct_day_numbers():
    """Days 1, 2, and 3 must all appear in the scheduled descriptors."""
    patchers = _patch_broadcast()
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
    """Only broadcast and h10 tasks are scheduled."""
    patchers = _patch_broadcast()
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

    assert {e["task"] for e in scheduled} == {"dispatch_broadcast", "dispatch_h10"}


def test_schedule_edition_can_limit_scheduling_to_one_live_day():
    """The ops page must schedule only the live day the client just saved."""
    patchers = _patch_broadcast()
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
    assert {entry["task"] for entry in scheduled} == {"dispatch_broadcast", "dispatch_h10"}


def test_schedule_edition_past_edition_skips_all():
    """An edition entirely in the past should produce 0 scheduled tasks."""
    patchers = _patch_broadcast()
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


def test_schedule_edition_broadcast_eta_is_h_minus_2():
    """The broadcast ETA must be 2 hours before live time."""
    broadcast_etas: list[datetime] = []

    def _capture_broadcast(**kwargs):
        eta = kwargs.get("eta")
        if eta:
            broadcast_etas.append(eta)
        return _fake_result()

    patchers = [
        patch.object(campaign_tasks.dispatch_broadcast, "apply_async", side_effect=_capture_broadcast),
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

    # 3 broadcast ETAs (one per day) — all at H-2 before the 19:00 EU live.
    assert len(broadcast_etas) == 3
