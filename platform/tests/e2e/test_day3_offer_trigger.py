"""Tests for POST /campaigns/trigger/day3-offer — removed in v5 journey.

The Day-3 H+2 offer endpoint and its heartbeat firing were removed when the
journey was simplified to 7 steps. These tests are kept as skipped stubs so
the git history preserves the original intent.
"""
import pytest

pytestmark = pytest.mark.skip(reason="/campaigns/trigger/day3-offer removed in v5 journey")


def test_day3_offer_sends_only_to_registered_contacts():
    pass


def test_day3_offer_respects_consent_gate():
    pass


def test_day3_offer_with_edition_key_filter():
    pass


def test_day3_offer_returns_zero_when_no_enrolled_contacts():
    pass


def test_day3_offer_skips_contacts_who_already_paid():
    pass
