"""Tests for closer email notification logic.

Validates:
  - should_notify_closer() returns True for high-intent intents / needs_human=True
  - notify_closer() gracefully degrades when SMTP is not configured
"""
import pytest

from services.notifications.app.email import (
    HIGH_INTENT_INTENTS,
    notify_closer,
    should_notify_closer,
)


# ── should_notify_closer ──────────────────────────────────────────────────────

@pytest.mark.parametrize("intent", [
    "conversion_intent_detected",
    "offer_interest_detected",
    "payment_failure_followup_needed",
    "installment_plan_request",
    "human_escalation",
])
def test_should_notify_on_high_intent(intent: str):
    assert should_notify_closer(intent, needs_human=False) is True


def test_should_notify_when_needs_human_true():
    assert should_notify_closer("default", needs_human=True) is True


def test_should_not_notify_for_generic_intent():
    assert should_notify_closer("faq_response", needs_human=False) is False


def test_should_not_notify_default_intent():
    assert should_notify_closer("default", needs_human=False) is False


# ── HIGH_INTENT_INTENTS set ───────────────────────────────────────────────────

def test_high_intent_intents_contains_expected_values():
    assert "conversion_intent_detected" in HIGH_INTENT_INTENTS
    assert "offer_interest_detected" in HIGH_INTENT_INTENTS
    assert "human_escalation" in HIGH_INTENT_INTENTS


# ── notify_closer: graceful degradation ──────────────────────────────────────

def test_notify_closer_returns_false_when_no_recipient(monkeypatch):
    import shared.config.settings as cfg_module
    monkeypatch.setattr(cfg_module.settings, "closer_notification_email", "")
    result = notify_closer(
        phone="+33600000001",
        contact_id="ct_abc",
        message_text="Je veux acheter",
        ai_reply="Voici le lien",
        intent="conversion_intent_detected",
        score=80,
    )
    assert result is False


def test_notify_closer_returns_false_when_no_smtp(monkeypatch):
    import shared.config.settings as cfg_module
    monkeypatch.setattr(cfg_module.settings, "closer_notification_email", "closer@team.com")
    monkeypatch.setattr(cfg_module.settings, "smtp_host", "")
    result = notify_closer(
        phone="+33600000001",
        contact_id="ct_abc",
        message_text="Je veux acheter",
        ai_reply="Voici le lien",
        intent="conversion_intent_detected",
        score=80,
    )
    assert result is False


def test_notify_closer_does_not_raise_when_smtp_misconfigured(monkeypatch):
    """Even with recipients + smtp_host, a connection error must not bubble up."""
    import shared.config.settings as cfg_module
    monkeypatch.setattr(cfg_module.settings, "closer_notification_email", "closer@team.com")
    monkeypatch.setattr(cfg_module.settings, "smtp_host", "localhost")
    monkeypatch.setattr(cfg_module.settings, "smtp_port", 9999)  # nothing running here
    monkeypatch.setattr(cfg_module.settings, "smtp_user", "u")
    monkeypatch.setattr(cfg_module.settings, "smtp_password", "p")
    monkeypatch.setattr(cfg_module.settings, "smtp_from", "noreply@example.com")

    # Should return False (send failure) — must NOT raise
    result = notify_closer(
        phone="+33600000001",
        contact_id="ct_abc",
        message_text="Je veux acheter le programme",
        ai_reply="Voici le lien de paiement",
        intent="conversion_intent_detected",
        score=95,
    )
    assert result is False
