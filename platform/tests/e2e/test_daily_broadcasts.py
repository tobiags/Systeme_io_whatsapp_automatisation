from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.campaigns.app.tasks import dispatch_daily_broadcasts
from shared.db.models import AuditEvent, CampaignEnrollment, ChallengeEdition, Consent, Message
from tests.conftest import _TestingSession, _engine

campaigns_client = TestClient(campaigns_app)


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
            current_step="COUNTDOWN_J1",
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
        result = dispatch_daily_broadcasts.run(now_iso="2026-05-23T17:30:00+00:00")
    assert result["processed"] == 1
    assert result["editions"][0]["queued"] == 1

    db = _TestingSession()
    try:
        messages = db.query(Message).all()
        assert len(messages) == 1
        assert messages[0].template_key == "countdown_j1_v1"

        audits = db.query(AuditEvent).all()
        assert len(audits) == 1
        assert audits[0].name == "campaign_daily_broadcast"
    finally:
        db.close()

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        second = dispatch_daily_broadcasts.run(now_iso="2026-05-23T18:00:00+00:00")
    assert second["processed"] == 0


def test_manual_edition_broadcast_blocks_scheduled_broadcast_same_local_day():
    _seed_edition(
        edition_key="2026-05-24-eu",
        cohort="EU",
        edition_date="2026-05-24",
    )

    with patch(
        "services.campaigns.app.main._local_broadcast_date",
        return_value=date(2026, 5, 23),
        create=True,
    ):
        manual = campaigns_client.post("/campaigns/broadcast", json={
            "campaign_key": "challenge-amazon-fba",
            "cohort": "EU",
            "edition_key": "2026-05-24-eu",
        })
    assert manual.status_code == 200
    assert manual.json()["queued"] == 1

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        scheduled = dispatch_daily_broadcasts.run(now_iso="2026-05-23T17:30:00+00:00")

    assert scheduled["processed"] == 0

    db = _TestingSession()
    try:
        messages = db.query(Message).all()
        assert len(messages) == 1
        assert messages[0].template_key == "countdown_j1_v1"

        audits = db.query(AuditEvent).all()
        assert len(audits) == 1
        assert audits[0].aggregate_id == "2026-05-24-eu:2026-05-23"
    finally:
        db.close()


def test_manual_edition_broadcast_does_not_send_day2_on_day1():
    db = _TestingSession()
    try:
        db.add(ChallengeEdition(
            id="ed_manual_day2",
            campaign_key="challenge-amazon-fba",
            edition_key="2026-05-28-usca",
            cohort="US-CA",
            edition_date="2026-05-28",
        ))
        db.add(CampaignEnrollment(
            id="enr_manual_day2",
            contact_id="ct_manual_day2",
            campaign_key="challenge-amazon-fba",
            edition_key="2026-05-28-usca",
            current_step="DAY_2",
            cohort="US-CA",
        ))
        db.add(Consent(
            contact_id="ct_manual_day2",
            status="opted_in",
            proof_source="test",
        ))
        db.commit()
    finally:
        db.close()

    with patch(
        "services.campaigns.app.main._local_broadcast_date",
        return_value=date(2026, 5, 28),
    ):
        too_early = campaigns_client.post("/campaigns/broadcast", json={
            "campaign_key": "challenge-amazon-fba",
            "cohort": "US-CA",
            "edition_key": "2026-05-28-usca",
        })

    assert too_early.status_code == 200
    assert too_early.json()["queued"] == 0

    db = _TestingSession()
    try:
        assert db.query(Message).count() == 0
        enrollment = db.query(CampaignEnrollment).filter_by(id="enr_manual_day2").one()
        assert enrollment.current_step == "DAY_2"
    finally:
        db.close()

    with patch(
        "services.campaigns.app.main._local_broadcast_date",
        return_value=date(2026, 5, 29),
    ):
        on_time = campaigns_client.post("/campaigns/broadcast", json={
            "campaign_key": "challenge-amazon-fba",
            "cohort": "US-CA",
            "edition_key": "2026-05-28-usca",
        })

    assert on_time.status_code == 200
    assert on_time.json()["queued"] == 1
    assert on_time.json()["messages"][0]["template_key"] == "live_day2_not_registered_v1"


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
        before_window = dispatch_daily_broadcasts.run(now_iso="2026-05-23T20:30:00+00:00")
    assert before_window["processed"] == 0

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        after_window = dispatch_daily_broadcasts.run(now_iso="2026-05-23T21:30:00+00:00")
    assert after_window["processed"] == 1


def test_daily_broadcasts_do_not_send_live_step_before_calendar_day():
    db = _TestingSession()
    try:
        db.add(ChallengeEdition(
            id="ed_future_day3",
            campaign_key="challenge-amazon-fba",
            edition_key="2026-05-28-usca",
            cohort="US-CA",
            edition_date="2026-05-28",
        ))
        db.add(CampaignEnrollment(
            id="enr_future_day3",
            contact_id="ct_future_day3",
            campaign_key="challenge-amazon-fba",
            edition_key="2026-05-28-usca",
            current_step="DAY_3",
            cohort="US-CA",
        ))
        db.add(Consent(
            contact_id="ct_future_day3",
            status="opted_in",
            proof_source="test",
        ))
        db.commit()
    finally:
        db.close()

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        too_early = dispatch_daily_broadcasts.run(now_iso="2026-05-29T21:30:00+00:00")

    assert too_early["processed"] == 1
    assert too_early["editions"][0]["queued"] == 0

    db = _TestingSession()
    try:
        assert db.query(Message).count() == 0
        enrollment = db.query(CampaignEnrollment).filter_by(id="enr_future_day3").one()
        assert enrollment.current_step == "DAY_3"
    finally:
        db.close()

    with patch(
        "services.campaigns.app.tasks.get_engine_and_session",
        return_value=(_engine, _TestingSession),
    ):
        on_time = dispatch_daily_broadcasts.run(now_iso="2026-05-30T21:30:00+00:00")

    assert on_time["processed"] == 1
    assert on_time["editions"][0]["queued"] == 1

    db = _TestingSession()
    try:
        message = db.query(Message).one()
        assert message.template_key == "live_day3_not_registered_v1"
    finally:
        db.close()
