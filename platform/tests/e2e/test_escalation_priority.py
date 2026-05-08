"""Tests for operator priority levels in the human escalation queue.

Spec §4 defines 3 priority levels:
  haute   — payment failure, installment plan, explicit call request
  moyenne — sceptic/trust objection, strong financial, email issue
  faible  — simple FAQ, next challenge request, generic financial
"""
from fastapi.testclient import TestClient

from services.integrations.app.main import app as integrations_app

client = TestClient(integrations_app)


def _send(phone: str, text: str) -> dict:
    resp = client.post("/webhooks/wati", json={"waId": phone, "text": {"body": text}})
    assert resp.status_code == 202
    return resp.json()


def _queue() -> list[dict]:
    resp = client.get("/webhooks/wati/queue")
    assert resp.status_code == 200
    return resp.json()


def test_payment_failure_priority_is_haute():
    _send("+3360001", "j'ai essayé de payer mais je n'avais pas assez sur mon compte")
    queue = _queue()
    entry = next(e for e in queue if e["phone"] == "+3360001")
    assert entry["intent"] == "payment_failure_followup_needed"
    assert entry["priority"] == "haute"


def test_installment_request_priority_is_haute():
    _send("+3360002", "est-ce que je peux payer en plusieurs fois ?")
    queue = _queue()
    entry = next(e for e in queue if e["phone"] == "+3360002")
    assert entry["intent"] == "installment_plan_request"
    assert entry["priority"] == "haute"


def test_human_escalation_priority_is_haute():
    _send("+3360003", "je veux un appel individuel avant de payer")
    queue = _queue()
    entry = next(e for e in queue if e["phone"] == "+3360003")
    assert entry["intent"] == "human_escalation"
    assert entry["priority"] == "haute"


def test_priority_field_present_on_all_queue_entries():
    """Every item returned by the queue endpoint must include a priority field."""
    _send("+3360010", "j'ai essayé de payer mais je n'avais pas assez")
    queue = _queue()
    for entry in queue:
        assert "priority" in entry
        assert entry["priority"] in {"haute", "moyenne", "faible"}
