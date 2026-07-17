"""Shared utilities for the campaigns service.

Centralises helpers used across main.py and tasks.py to avoid drift
between duplicate implementations.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import date

import redis

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(_REDIS_URL, decode_responses=True)
    return _redis_client


@contextmanager
def redis_lock(lock_key: str, timeout: int):
    """Generic distributed Redis lock (non-blocking).

    Yields True if acquired, False if another process holds it.
    Auto-expires after `timeout` seconds if the holder crashes.

    DEGRADED MODE: if Redis is unreachable, yields True and proceeds WITHOUT
    the lock — the AuditEvent SELECT check + UNIQUE constraint remain as
    protection. A Redis outage must never block message delivery.
    """
    lock = None
    acquired = False
    degraded = False
    try:
        r = _get_redis()
        lock = r.lock(lock_key, timeout=timeout, blocking=False)
        acquired = lock.acquire(blocking=False)
    except redis.exceptions.RedisError as exc:
        logger.warning("redis_lock '%s' unavailable (%s) — proceeding without lock", lock_key, exc)
        degraded = True
    try:
        yield acquired or degraded
    finally:
        if acquired and lock is not None:
            try:
                lock.release()
            except redis.exceptions.RedisError:
                pass


def broadcast_lock(edition_key: str, local_day: date, timeout: int = 1800):
    """Distributed Redis lock preventing concurrent broadcasts for the same edition+day.

    Acquired BEFORE the SELECT check, released AFTER the audit INSERT.
    timeout = 1800s (30 min): a 600+ contact broadcast with rate-limit throttling
    takes ~6-10 min, so the lock must outlive the slowest realistic broadcast.
    If the worker crashes mid-broadcast, the lock auto-expires and the next
    beat tick can retry.
    """
    return redis_lock(f"broadcast_lock:{edition_key}:{local_day.isoformat()}", timeout)


# ── Broadcast idempotency helpers ─────────────────────────────────────────────

def broadcast_audit_id(edition_key: str, local_day: date) -> str:
    """Canonical aggregate_id for a campaign_daily_broadcast AuditEvent."""
    return f"{edition_key}:{local_day.isoformat()}"


def broadcast_already_recorded(db, edition_key: str, local_day: date) -> bool:
    """Return True if a broadcast AuditEvent already exists for this edition+day.

    Single source of truth — used by both main.py and tasks.py so the two
    implementations cannot drift and produce duplicate broadcasts.
    """
    from shared.db.models import AuditEvent  # local import avoids circular deps

    return (
        db.query(AuditEvent)
        .filter(
            AuditEvent.name == "campaign_daily_broadcast",
            AuditEvent.aggregate_id == broadcast_audit_id(edition_key, local_day),
        )
        .first()
        is not None
    )


# ── Wati UTILITY template registry ───────────────────────────────────────────
#
# v1 journey (re-submitted 2026-07 after the v7 spam flag): 12 templates are
# UTILITY, 6 are MARKETING (live_day3_h2_v1, live_day3_h90_v1, post_replay_v1,
# post_testimonials_v1, post_closer_v1, post_closer_call_v1).
# MARKETING templates are filtered for US/CA numbers by Meta — no UTILITY
# variant exists for these, so resolve_template_key remains a pass-through.
# TEMPLATES_WITH_UTILITY is kept empty (no dual UTILITY/MARKETING variants).
TEMPLATES_WITH_UTILITY: frozenset[str] = frozenset()


def _is_us_ca_phone(phone: str) -> bool:
    """True for US/Canada numbers (11 digits starting with '1') after normalisation.

    Meta blocks MARKETING category templates for these numbers.
    Use UTILITY template variants (same content, different Meta category) instead —
    but ONLY when the variant is registered in TEMPLATES_WITH_UTILITY, because
    routing to a non-existent template causes a silent Wati error and leaves the
    contact stuck at the wrong journey step.
    """
    p = phone.strip()
    if p.startswith("+"):
        p = p[1:]
    elif p.startswith("00"):
        p = p[2:]
    return len(p) == 11 and p.startswith("1")


def resolve_template_key(template_key: str, phone: str) -> str:
    """Return the template key to use for the given phone.

    v7: MARKETING templates are sent as-is even for US/CA contacts (no UTILITY
    variant registered). Pass-through kept for call-site compatibility.
    """
    return template_key
