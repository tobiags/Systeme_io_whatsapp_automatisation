import httpx

from services.messaging.app.providers.wati import WatiProvider


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.content = b"{}"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self._response


def test_wati_provider_send_text_marks_result_false_as_failed(monkeypatch):
    fake_client = _FakeClient(_FakeResponse({"result": False, "message": "session closed"}))
    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: fake_client)

    provider = WatiProvider("https://eu.wati.io/1116186", "token")
    result = provider.send_text("+22900000001", "Bonjour")

    assert result["status"] == "failed"
    assert "session closed" in result["error"]


def test_wati_provider_send_text_returns_queued_on_success(monkeypatch):
    fake_client = _FakeClient(_FakeResponse({"result": True, "messageId": "wati_msg_1"}))
    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: fake_client)

    provider = WatiProvider("https://eu.wati.io/1116186", "token")
    result = provider.send_text("+22900000001", "Bonjour")

    assert result["status"] == "queued"
    assert result["provider_message_id"] == "wati_msg_1"
