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
# Meta blocks MARKETING category templates for US/CA (+1) numbers.
# We route those contacts to _utility variants — BUT only when the variant
# actually exists in Wati.  Adding a template to this set means:
#   1. The Wati template "{name}_utility" has been created & approved.
#   2. Both base and _utility carry the same message content.
#
# HOW TO UPDATE: whenever you create a new _utility variant in Wati, add
# its BASE name here (without the "_utility" suffix).
#
# Templates confirmed to have an approved _utility variant.
# NOTE: All templates renamed with _v2/_v3 suffix after Wati blocked originals
# (originals deleted and Wati keeps names in memory for ~30 days).
# Convention: base name → base_name_utility (same body, UTILITY category).
TEMPLATES_WITH_UTILITY: frozenset[str] = frozenset({
    # ── Phase 1 — Pré-challenge (_v2 batch) ────────────────────────────────
    "welcome_v2",
    "countdown_j1_v2",
    "countdown_j2_v2",
    "countdown_j3_v2",
    "countdown_j4_v2",
    "countdown_j5_v2",
    "countdown_j6_v2",
    # ── Day 1 (_v2 batch) ──────────────────────────────────────────────────
    "live_day1_v2",
    "live_day1_h10_v4",
    "live_day1_hplus5_v4",
    # ── Day 2 (_v2/_v3/_v4 batch) ─────────────────────────────────────────
    "live_day2_attended_v3",
    "live_day2_h10_v4",
    "live_day2_hplus5_v4",
    "live_day2_not_registered_v2",
    "live_day2_registered_absent_v2",
    # ── Day 3 (_v2/_v3/_v4 batch) ─────────────────────────────────────────
    "live_day3_attended_v3",
    "live_day3_h10_v4",
    "live_day3_hplus5_v4",
    "live_day3_not_registered_v2",
    "live_day3_offer_hplus2_v2",
    "live_day3_offer_hplus3_v4",
    "live_day3_registered_absent_v2",
    # ── Post-challenge (_v2/_v4 batch) ────────────────────────────────────
    "post_recap_attended_v4",
    "post_recap_registered_absent_v4",
    "post_recap_not_registered_v4",
    "post_testimonials_v2",
    "post_inaction_reason_v2",
    "post_closer_call_v4",
})


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
    """Return the correct template key for the given phone, applying US/CA routing.

    If the phone is a US/CA number AND the template has an approved _utility
    variant, returns ``template_key + "_utility"``.  Otherwise returns the
    template_key unchanged — even for US/CA numbers — rather than routing to a
    non-existent template and causing a silent failure.

    Args:
        template_key: Base template key (without ``_utility`` suffix).
        phone: Recipient phone number (any format — normalised internally).

    Returns:
        The effective template key to pass to the messaging provider.
    """
    if not _is_us_ca_phone(phone):
        return template_key

    if template_key in TEMPLATES_WITH_UTILITY:
        return template_key + "_utility"

    # Template has no _utility variant yet.  Log a warning so the issue is
    # visible in Sentry / CloudWatch and fall back to the MARKETING template.
    # For EU contacts this is fine.  For US/CA contacts Meta may reject it —
    # but at least it's auditable and the contact isn't permanently stuck.
    logger.warning(
        "resolve_template_key: no _utility variant for '%s' — "
        "sending MARKETING template to US/CA number (may be rejected by Meta). "
        "Create '%s_utility' in Wati and add it to TEMPLATES_WITH_UTILITY.",
        template_key,
        template_key,
    )
    return template_key
