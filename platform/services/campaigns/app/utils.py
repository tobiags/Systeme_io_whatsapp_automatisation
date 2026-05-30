"""Shared utilities for the campaigns service.

Centralises helpers used across main.py and tasks.py to avoid drift
between duplicate implementations.
"""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


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
# Templates confirmed to have an approved _utility variant (last updated: 2026-05-30):
TEMPLATES_WITH_UTILITY: frozenset[str] = frozenset({
    # ── Inscription / Compte à rebours (créés 2026-05-30) ──────────────────
    # "welcome",              # welcome_utility ❌ pas encore créé dans Wati
    "welcome_v2_entry",       # welcome_v2_entry_utility ✅
    "countdown_j1",           # countdown_j1_utility ✅
    "countdown_j2",           # countdown_j2_utility ✅
    "countdown_j3",           # countdown_j3_utility ✅
    "countdown_j4",           # countdown_j4_utility ✅
    "countdown_j5",           # countdown_j5_utility ✅
    "countdown_j6",           # countdown_j6_utility ✅
    # ── Day 1 (créés 2026-05-30) ───────────────────────────────────────────
    "live_day1",              # live_day1_utility ✅
    "live_day1_h10",          # live_day1_h10_utility ✅
    "live_day1_hplus5",       # live_day1_hplus5_utility ✅
    # ── Day 2 (créés 2026-05-29) ───────────────────────────────────────────
    "live_day2_attended_v2",
    "live_day2_h10",
    "live_day2_hplus5",
    "live_day2_not_registered",
    "live_day2_registered_absent",
    # ── Day 3 (créés 2026-05-29) ───────────────────────────────────────────
    "live_day3_attended_v2",
    "live_day3_h10",
    "live_day3_hplus5",
    "live_day3_not_registered",
    "live_day3_offer_hplus2",
    "live_day3_registered_absent",
    # ── Post-challenge (créés 2026-05-30) ──────────────────────────────────
    "post_recap_attended",           # post_recap_attended_utility ✅
    "post_recap_registered_absent",  # post_recap_registered_absent_utility ✅
    "post_recap_not_registered",     # post_recap_not_registered_utility ✅
    "post_testimonials",             # post_testimonials_utility ✅
    "post_inaction_reason",          # post_inaction_reason_utility ✅
    "post_closer_call",              # post_closer_call_utility ✅
    # ── Seul manquant ──────────────────────────────────────────────────────
    # "welcome",              # → welcome_utility  (à créer dans Wati)
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
