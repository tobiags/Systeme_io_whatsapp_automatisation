"""Tests for the next_challenge_request intent (spec §7.3).

Distinct from faq_next_challenge_date (asking when):
next_challenge_request = contact explicitly deferring to a future edition.
"""
from fastapi.testclient import TestClient

from services.conversation_ai.app.main import app

client = TestClient(app)


def test_deferral_phrase_triggers_next_challenge_request():
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_1",
        "message": "je reviendrai plus tard pour m'inscrire",
    })
    assert resp.status_code == 200
    assert resp.json()["intent"] == "next_challenge_request"
    assert resp.json()["needs_human"] is False


def test_prochaine_fois_triggers_next_challenge_request():
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_2",
        "message": "je le ferai la prochaine fois",
    })
    assert resp.status_code == 200
    assert resp.json()["intent"] == "next_challenge_request"


def test_next_challenge_request_reply_mentions_frequency():
    """The reply should remind the contact the challenge runs twice a month."""
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_3",
        "message": "je reviendrai plus tard",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "next_challenge_request"
    assert "2 fois par mois" in body["reply"]


def test_faq_next_challenge_date_not_confused_with_deferral():
    """Asking 'when is the next challenge' → faq_next_challenge_date (not deferral)."""
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_4",
        "message": "quand est-ce que vous referez un nouveau challenge ?",
    })
    assert resp.status_code == 200
    assert resp.json()["intent"] == "faq_next_challenge_date"
