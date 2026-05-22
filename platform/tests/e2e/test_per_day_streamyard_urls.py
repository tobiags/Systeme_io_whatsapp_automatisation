"""Tests for per-day StreamYard URL routing in streamyard_session + _build_variables."""
from fastapi.testclient import TestClient

from services.campaigns.app.main import _build_variables
from services.integrations.app.main import app as integrations_app

integrations_client = TestClient(integrations_app)


class _FakeEdition:
    def __init__(self, day1_url=None, day2_url=None, day3_url=None, streamyard_url=None):
        self.day1_url = day1_url
        self.day2_url = day2_url
        self.day3_url = day3_url
        self.streamyard_url = streamyard_url


def test_live_day1_uses_day1_url():
    edition = _FakeEdition(day1_url="https://streamyard.com/day1", streamyard_url="https://streamyard.com/fallback")
    variables = _build_variables("Marie", "live_day1", edition, "EU")
    assert variables["2"] == "https://streamyard.com/day1"


def test_live_day2_attended_v2_uses_day2_url():
    edition = _FakeEdition(day2_url="https://streamyard.com/day2", streamyard_url="https://streamyard.com/fallback")
    variables = _build_variables("Marie", "live_day2_attended_v2", edition, "EU")
    assert variables["2"] == "https://streamyard.com/day2"


def test_live_day2_registered_absent_h2_uses_day2_url():
    edition = _FakeEdition(day2_url="https://streamyard.com/day2")
    variables = _build_variables("Kofi", "live_day2_registered_absent", edition, "EU")
    assert variables["2"] == "https://streamyard.com/day2"


def test_live_day3_attended_v2_uses_day3_url():
    edition = _FakeEdition(day3_url="https://streamyard.com/day3", streamyard_url="https://streamyard.com/fallback")
    variables = _build_variables("Jean", "live_day3_attended_v2", edition, "EU")
    assert variables["2"] == "https://streamyard.com/day3"


def test_live_day3_fallback_to_streamyard_url_when_day3_url_not_set():
    edition = _FakeEdition(day3_url=None, streamyard_url="https://streamyard.com/legacy")
    variables = _build_variables("Jean", "live_day3_attended_v2", edition, "EU")
    assert variables["2"] == "https://streamyard.com/legacy"


def test_live_day1_fallback_when_no_per_day_url():
    edition = _FakeEdition(day1_url=None, streamyard_url="https://streamyard.com/legacy")
    variables = _build_variables("Ada", "live_day1", edition, "EU")
    assert variables["2"] == "https://streamyard.com/legacy"


def test_live_day_no_edition_returns_empty_url():
    variables = _build_variables("Ada", "live_day2_attended_v2", None, "EU")
    assert variables["2"] == ""


def test_live_day3_offer_hplus2_uses_program_payment_url(monkeypatch):
    import shared.config.settings as cfg_module

    monkeypatch.setattr(cfg_module.settings, "program_payment_url", "https://pay.example.com/fba")
    from services.campaigns.app.main import _build_variables as bv

    variables = bv("Lea", "live_day3_offer_hplus2", None, "EU")
    assert variables["2"] == "https://pay.example.com/fba"


def test_post_recap_replay_templates_use_replay_urls(monkeypatch):
    import shared.config.settings as cfg_module

    monkeypatch.setattr(cfg_module.settings, "replay_day1_url", "https://replay.example.com/day1")
    monkeypatch.setattr(cfg_module.settings, "replay_day2_url", "https://replay.example.com/day2")
    monkeypatch.setattr(cfg_module.settings, "replay_day3_url", "https://replay.example.com/day3")
    from services.campaigns.app.main import _build_variables as bv

    variables = bv("Lea", "post_recap_registered_absent", None, "EU")
    assert variables["2"] == "https://replay.example.com/day1"
    assert variables["3"] == "https://replay.example.com/day2"
    assert variables["4"] == "https://replay.example.com/day3"


def test_post_recap_attended_uses_oncehub_url(monkeypatch):
    import shared.config.settings as cfg_module

    monkeypatch.setattr(cfg_module.settings, "oncehub_form_url", "https://www.ecommercecentrale.com/formulaire-challenge")
    from services.campaigns.app.main import _build_variables as bv

    variables = bv("Lea", "post_recap_attended", None, "EU")
    assert variables["2"] == "https://www.ecommercecentrale.com/formulaire-challenge"


def test_post_closer_call_uses_oncehub_url(monkeypatch):
    import shared.config.settings as cfg_module

    monkeypatch.setattr(cfg_module.settings, "oncehub_form_url", "https://www.ecommercecentrale.com/formulaire-challenge")
    from services.campaigns.app.main import _build_variables as bv

    variables = bv("Bob", "post_closer_call", None, "EU")
    assert variables["2"] == "https://www.ecommercecentrale.com/formulaire-challenge"


def test_streamyard_session_stores_day1_url():
    resp = integrations_client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": "2026-06-01-eu",
        "region": "EU",
        "join_url": "https://streamyard.com/day1-link",
        "day_number": 1,
    })
    assert resp.status_code == 202
    assert resp.json()["stored"] is True
    assert resp.json()["day_number"] == 1


def test_streamyard_session_stores_day2_url():
    resp = integrations_client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": "2026-06-01-eu",
        "region": "EU",
        "join_url": "https://streamyard.com/day2-link",
        "day_number": 2,
    })
    assert resp.status_code == 202
    assert resp.json()["day_number"] == 2


def test_streamyard_session_stores_day3_url():
    resp = integrations_client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": "2026-06-01-eu",
        "region": "EU",
        "join_url": "https://streamyard.com/day3-link",
        "day_number": 3,
    })
    assert resp.status_code == 202
    assert resp.json()["day_number"] == 3


def test_streamyard_session_without_day_number_uses_legacy_url():
    resp = integrations_client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": "2026-06-02-eu",
        "region": "EU",
        "join_url": "https://streamyard.com/generic-link",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert body["join_url"] == "https://streamyard.com/generic-link"
    assert body.get("day_number") is None
