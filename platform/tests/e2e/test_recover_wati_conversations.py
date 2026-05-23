from datetime import datetime, timedelta, timezone

from scripts.recover_wati_conversations import _iter_recoverable_inbounds
from shared.db.models import Contact, InboundMessage, Message
from tests.conftest import _TestingSession


def _now():
    return datetime.now(timezone.utc)


def test_recover_wati_conversations_includes_stale_queued_followups():
    db = _TestingSession()
    try:
        contact = Contact(id="ct_recover_1", phone="22900000111", first_name="Awa", source="test")
        db.add(contact)
        db.commit()

        inbound = InboundMessage(
            phone="22900000111",
            contact_id=contact.id,
            text="Je pars de zéro",
            ai_reply="Ancienne réponse",
            intent="default",
            needs_human=False,
            received_at=_now() - timedelta(minutes=30),
        )
        db.add(inbound)
        db.commit()

        stale_reply = Message(
            id="msg_old_queued",
            contact_id=contact.id,
            template_key="ai_session_reply",
            variables={"text": "Réponse fantôme"},
            status="queued",
            provider="wati",
            created_at=_now() - timedelta(minutes=25),
        )
        db.add(stale_reply)
        db.commit()

        rows = _iter_recoverable_inbounds(db, limit=10, stale_minutes=15)
        assert [row.phone for row in rows] == ["22900000111"]
    finally:
        db.close()


def test_recover_wati_conversations_skips_recent_queued_followups():
    db = _TestingSession()
    try:
        contact = Contact(id="ct_recover_2", phone="22900000112", first_name="Mira", source="test")
        db.add(contact)
        db.commit()

        inbound = InboundMessage(
            phone="22900000112",
            contact_id=contact.id,
            text="Bonjour",
            ai_reply="Réponse récente",
            intent="default",
            needs_human=False,
            received_at=_now() - timedelta(minutes=3),
        )
        db.add(inbound)
        db.commit()

        fresh_reply = Message(
            id="msg_recent_queued",
            contact_id=contact.id,
            template_key="ai_session_reply",
            variables={"text": "Réponse récente"},
            status="queued",
            provider="wati",
            created_at=_now() - timedelta(minutes=2),
        )
        db.add(fresh_reply)
        db.commit()

        rows = _iter_recoverable_inbounds(db, limit=10, stale_minutes=15)
        assert rows == []
    finally:
        db.close()
