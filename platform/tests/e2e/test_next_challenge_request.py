"""Tests for the next_challenge_request intent (spec Â§7.3).

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
    assert resp.json()["intent"] == "soft_open_invitation"
    assert resp.json()["needs_human"] is False


def test_prochaine_fois_triggers_next_challenge_request():
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_2",
        "message": "je le ferai la prochaine fois",
    })
    assert resp.status_code == 200
    assert resp.json()["intent"] == "soft_open_invitation"


def test_next_challenge_request_reply_stays_soft_open():
    """A deferral now falls back to a soft invitation instead of a sales reply."""
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_3",
        "message": "je reviendrai plus tard",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "soft_open_invitation"
    assert "question sur le challenge" in body["reply"].lower()


def test_faq_next_challenge_date_not_confused_with_deferral():
    """Asking 'when is the next challenge' â†’ faq_next_challenge_date (not deferral)."""
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_ncr_4",
        "message": "quand est-ce que vous referez un nouveau challenge ?",
    })
    assert resp.status_code == 200
    assert resp.json()["intent"] == "clarification_request"
