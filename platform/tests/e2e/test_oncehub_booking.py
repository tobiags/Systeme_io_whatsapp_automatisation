"""Tests for POST /webhooks/oncehub/booking.

Covers:
  - Contact lookup by phone (primary) and email (fallback)
  - Contact not found → 200 "ignored" (never 4xx — OnceHub would retry on error)
  - Invalid JSON body → 400
  - HMAC signature validation (valid / invalid / missing / secret not configured)
  - Phone number normalisation (strips +, spaces, dashes)
  - Wati assignment skipped when WATI_CLOSER_EMAIL not set
  - Email graceful degradation (SMTP not configured → ok, no exception)
  - Booking metadata forwarded in response (booking_start, booking_page)
"""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from services.integrations.app.main import app
from shared.db.models import Contact, Consent, ContactScore, Segment
from shared.db.session import get_db

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sign(body: bytes, secret: str) -> str:
    """Compute the OnceHub HMAC-SHA256 signature header value."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(payload: dict, secret: str | None = None, extra_headers: dict | None = None):
    """POST to /webhooks/oncehub/booking, optionally with HMAC signature."""
    body = json.dumps(payload).encode()
    headers = {"content-type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    if secret:
        headers["X-Hub-Signature"] = _sign(body, secret)
    return client.post("/webhooks/oncehub/booking", content=body, headers=headers)


def _seed_contact(db_session, phone: str = "22997551273", email: str | None = "test@example.com") -> Contact:
    contact = Contact(id="ct_onch_test", phone=phone, email=email, first_name="Jean", source="test")
    db_session.add(contact)
    db_session.commit()
    return contact


def _get_db_session():
    """Return the overridden DB session from the app's dependency."""
    gen = app.dependency_overrides[get_db]()
    return next(gen)


# ── Payload constants ─────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "contact": {
        "name": "Jean Dupont",
        "email": "test@example.com",
        "phone_number": "+22997551273",
    },
    "booking": {
        "start_time": "2026-06-20T10:00:00Z",
    },
    "booking_page": {
        "name": "Appel closing Amazon FBA",
    },
}

PAYLOAD_EMAIL_ONLY = {
    "contact": {
        "name": "Jean Dupont",
        "email": "test@example.com",
    },
    "booking": {"start_time": "2026-06-20T10:00:00Z"},
}

PAYLOAD_UNKNOWN_CONTACT = {
    "contact": {
        "name": "Inconnu",
        "email": "nobody@nowhere.com",
        "phone_number": "+33699999999",
    },
}


# ── Contact found by phone ────────────────────────────────────────────────────

def test_booking_found_by_phone(monkeypatch):
    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    resp = _post(VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["contact_id"] == "ct_onch_test"
    assert body["phone"] == "22997551273"
    assert body["first_name"] == "Jean"
    assert body["booking_start"] == "2026-06-20T10:00:00Z"
    assert body["booking_page"] == "Appel closing Amazon FBA"


def test_booking_found_by_email_fallback(monkeypatch):
    """When phone is absent from payload, lookup falls back to email."""
    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    resp = _post(PAYLOAD_EMAIL_ONLY)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["contact_id"] == "ct_onch_test"


# ── Contact not found ─────────────────────────────────────────────────────────

def test_booking_contact_not_found_returns_ignored(monkeypatch):
    """Unknown contact must NOT return an error — OnceHub retries on non-2xx."""
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")

    resp = _post(PAYLOAD_UNKNOWN_CONTACT)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ignored"
    assert body["reason"] == "contact_not_found"


def test_booking_no_phone_no_email_returns_ignored(monkeypatch):
    """Empty payload with no identifiers → ignored."""
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")

    resp = _post({"booking": {"start_time": "2026-06-20T10:00:00Z"}})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


# ── Invalid JSON ──────────────────────────────────────────────────────────────

def test_booking_invalid_json_returns_400(monkeypatch):
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")

    resp = client.post(
        "/webhooks/oncehub/booking",
        content=b"not json at all",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400


# ── HMAC signature validation ─────────────────────────────────────────────────

def test_valid_hmac_signature_passes(monkeypatch):
    db = _get_db_session()
    _seed_contact(db)

    secret = "mysecret123"
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", secret)
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    resp = _post(VALID_PAYLOAD, secret=secret)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_invalid_hmac_signature_returns_401(monkeypatch):
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "correct_secret")

    body = json.dumps(VALID_PAYLOAD).encode()
    resp = client.post(
        "/webhooks/oncehub/booking",
        content=body,
        headers={
            "content-type": "application/json",
            "X-Hub-Signature": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
        },
    )
    assert resp.status_code == 401


def test_missing_signature_header_when_secret_set_returns_401(monkeypatch):
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "mysecret")

    resp = _post(VALID_PAYLOAD)  # no secret arg → no header sent
    assert resp.status_code == 401


def test_no_secret_configured_skips_validation(monkeypatch):
    """If ONCEHUB_WEBHOOK_SECRET is empty, any request passes — even without header."""
    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    resp = _post(VALID_PAYLOAD)  # no signature
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Phone normalisation ───────────────────────────────────────────────────────

@pytest.mark.parametrize("raw_phone", [
    "+229 97 55 12 73",
    "+229-97-55-12-73",
    "+229.97.55.12.73",
    "22997551273",
    "+22997551273",
])
def test_phone_normalisation_finds_contact(raw_phone, monkeypatch):
    db = _get_db_session()
    _seed_contact(db, phone="22997551273")

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    payload = {"contact": {"phone_number": raw_phone, "email": "x@x.com"}}
    resp = _post(payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Wati assignment ───────────────────────────────────────────────────────────

def test_wati_assignment_skipped_when_no_closer_email(monkeypatch):
    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    resp = _post(VALID_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["wati_assigned"] is False


def test_wati_assignment_attempted_when_closer_email_set(monkeypatch):
    """With a closer email configured, assign_to_operator is called."""
    from services.messaging.app.providers.wati import WatiProvider

    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "closer@team.com")

    fake = _FakeWatiProvider()
    # Make isinstance(fake, WatiProvider) pass without a real Wati connection
    monkeypatch.setattr("services.integrations.app.main.WatiProvider", type(fake))
    monkeypatch.setattr("services.integrations.app.main._get_provider", lambda: fake)

    resp = _post(VALID_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["wati_assigned"] is True


class _FakeWatiProvider:
    """Mimics WatiProvider interface — passes isinstance check via monkeypatching."""
    def assign_to_operator(self, phone: str, assignee_email: str) -> bool:
        return True


# ── Email graceful degradation ────────────────────────────────────────────────

def test_email_failure_does_not_break_response(monkeypatch):
    """Even if send_prospect_summary fails, the endpoint must return 200."""
    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")
    monkeypatch.setattr("shared.config.settings.settings.closer_notification_email", "closer@team.com")
    monkeypatch.setattr("shared.config.settings.settings.smtp_host", "localhost")
    monkeypatch.setattr("shared.config.settings.settings.smtp_port", 9999)  # nothing running

    resp = _post(VALID_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Response fields completeness ─────────────────────────────────────────────

def test_response_contains_all_expected_fields(monkeypatch):
    db = _get_db_session()
    _seed_contact(db)

    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", "")
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    resp = _post(VALID_PAYLOAD)
    body = resp.json()

    for field in ("status", "contact_id", "phone", "first_name", "score",
                  "segment", "templates_count", "exchanges_count",
                  "wati_assigned", "booking_start", "booking_page"):
        assert field in body, f"Missing field: {field}"

    assert isinstance(body["templates_count"], int)
    assert isinstance(body["exchanges_count"], int)
    assert isinstance(body["wati_assigned"], bool)


# ── Alternative header name ───────────────────────────────────────────────────

def test_x_hub_signature_256_header_also_accepted(monkeypatch):
    """OnceHub may send X-Hub-Signature-256 — must be accepted too."""
    db = _get_db_session()
    _seed_contact(db)

    secret = "altsecret"
    monkeypatch.setattr("shared.config.settings.settings.oncehub_webhook_secret", secret)
    monkeypatch.setattr("shared.config.settings.settings.wati_closer_email", "")

    body = json.dumps(VALID_PAYLOAD).encode()
    sig = _sign(body, secret)
    resp = client.post(
        "/webhooks/oncehub/booking",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
