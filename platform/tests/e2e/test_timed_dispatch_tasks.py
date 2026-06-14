"""Tests for timed challenge reminder dispatch tasks."""
from fastapi.testclient import TestClient

from services.campaigns.app import tasks as campaign_tasks
from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.contacts.app.main import app as contacts_app
from services.scoring.app.main import app as scoring_app
from tests.conftest import _TestingSession
from shared.db.models import ChallengeEdition, Message

campaigns_client = TestClient(campaigns_app)
consent_client = TestClient(consent_app)
contacts_client = TestClient(contacts_app)
scoring_client = TestClient(scoring_app)

CAMPAIGN_KEY = "challenge-amazon-fba"
COHORT = "EU"
EDITION_KEY = "2030-05-21-eu"


class _FakeProvider:
    def send_template(self, phone: str, template_key: str, variables: dict[str, str]) -> dict:
        return {
            "provider": "mock",
            "provider_message_id": f"mock_{phone}_{template_key}",
            "status": "queued",
        }


def _patch_task_db(monkeypatch) -> None:
    monkeypatch.setattr(campaign_tasks, "get_engine_and_session", lambda: (None, _TestingSession))


def _create_contact(phone: str, first_name: str) -> str:
    resp = contacts_client.post("/contacts", json={
        "phone": phone,
        "first_name": first_name,
        "source": "test",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def _grant_consent(contact_id: str) -> None:
    resp = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "test",
    })
    assert resp.status_code == 201


def _enroll(contact_id: str) -> None:
    resp = campaigns_client.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": CAMPAIGN_KEY,
        "region": COHORT,
        "edition_key": EDITION_KEY,
    })
    assert resp.status_code == 201


def _record_event(contact_id: str, event_type: str) -> None:
    resp = scoring_client.post("/scores/events", json={
        "contact_id": contact_id,
        "event_type": event_type,
    })
    assert resp.status_code in (200, 201)


def test_dispatch_h10_skips_no_consent_and_paid_offer(monkeypatch):
    monkeypatch.setattr(campaign_tasks, "_get_provider", lambda: _FakeProvider())
    _patch_task_db(monkeypatch)

    ct_h10_ok = _create_contact("+33600000051", "Nina")
    ct_h10_no_consent = _create_contact("+33600000052", "Omar")
    ct_h10_paid = _create_contact("+33600000053", "Paul")

    _grant_consent(ct_h10_ok)
    _grant_consent(ct_h10_paid)

    for contact_id in (ct_h10_ok, ct_h10_no_consent, ct_h10_paid):
        _enroll(contact_id)

    _record_event(ct_h10_paid, "paid_offer")

    result = campaign_tasks.dispatch_h10.run(
        campaign_key=CAMPAIGN_KEY,
        cohort=COHORT,
        day_number=3,
        edition_key=EDITION_KEY,
        streamyard_url="https://streamyard.com/day3",
    )
    assert result["dispatched"] == 1

    db = _TestingSession()
    try:
        rows = db.query(Message).all()
        assert len(rows) == 1
        assert rows[0].contact_id == ct_h10_ok
        assert rows[0].template_key == "live_day3_h10_v5"
    finally:
        db.close()


def test_dispatch_h10_resolves_per_day_streamyard_url_from_edition(monkeypatch):
    monkeypatch.setattr(campaign_tasks, "_get_provider", lambda: _FakeProvider())
    _patch_task_db(monkeypatch)

    contact_id = _create_contact("+33600000061", "Rima")
    _grant_consent(contact_id)
    _enroll(contact_id)

    db = _TestingSession()
    try:
        db.add(ChallengeEdition(
            id="ed_timed_urls",
            campaign_key=CAMPAIGN_KEY,
            edition_key=EDITION_KEY,
            cohort=COHORT,
            edition_date="2030-05-21",
            day1_url="https://streamyard.com/day1",
            day2_url="https://streamyard.com/day2",
            day3_url="https://streamyard.com/day3",
        ))
        db.commit()
    finally:
        db.close()

    result = campaign_tasks.dispatch_h10.run(
        campaign_key=CAMPAIGN_KEY,
        cohort=COHORT,
        day_number=2,
        edition_key=EDITION_KEY,
        streamyard_url="https://streamyard.com/wrong-day",
    )
    assert result["dispatched"] == 1

    db = _TestingSession()
    try:
        row = db.query(Message).filter(Message.contact_id == contact_id).one()
        assert row.variables["2"] == "https://streamyard.com/day2"
    finally:
        db.close()
