from unittest.mock import patch

from services.campaigns.app.tasks import dispatch_daily_broadcasts
from shared.db.models import AuditEvent, CampaignEnrollment, ChallengeEdition, Consent, Message
from tests.conftest import _TestingSession, _engine


def _seed_edition(*, edition_key: str, cohort: str, edition_date: str) -> None:
    db = _TestingSession()
    try:
        db.add(ChallengeEdition(
            id=f"ed_{edition_key[-4:]}",
            campaign_key="challenge-amazon-fba",
            edition_key=edition_key,
            cohort=cohort,
            edition_date=edition_date,
        ))
        db.add(CampaignEnrollment(
            id=f"enr_{edition_key[-4:]}",
            contact_id=f"ct_{edition_key[-4:]}",
            campaign_key="challenge-amazon-fba",
            edition_key=edition_key,
            current_step="COUNTDOWN_J5",
            cohort=cohort,
        ))
        db.add(Consent(
            contact_id=f"ct_{edition_key[-4:]}",
            status="opted_in",
            proof_source="test",
        ))
        db.commit()
    finally:
        db.close()


def test_daily_broadcasts_send_once_per_local_day_for_active_edition():
    _seed_edition(
        edition_key="2026-05-24-eu",
        cohort="EU",
        edition_date="2026-05-24",
    )

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        result = dispatch_daily_broadcasts.run(now_iso="2026-05-19T08:30:00+00:00")
    assert result["processed"] == 1
    assert result["editions"][0]["queued"] == 1

    db = _TestingSession()
    try:
        messages = db.query(Message).all()
        assert len(messages) == 1
        assert messages[0].template_key == "countdown_j5"

        audits = db.query(AuditEvent).all()
        assert len(audits) == 1
        assert audits[0].name == "campaign_daily_broadcast"
    finally:
        db.close()

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        second = dispatch_daily_broadcasts.run(now_iso="2026-05-19T09:00:00+00:00")
    assert second["processed"] == 0


def test_daily_broadcasts_wait_until_local_broadcast_time():
    _seed_edition(
        edition_key="2026-05-24-usca",
        cohort="US-CA",
        edition_date="2026-05-24",
    )

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        before_window = dispatch_daily_broadcasts.run(now_iso="2026-05-19T11:30:00+00:00")
    assert before_window["processed"] == 0

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        after_window = dispatch_daily_broadcasts.run(now_iso="2026-05-19T14:30:00+00:00")
    assert after_window["processed"] == 1
