from fastapi.testclient import TestClient

from services.conversation_ai.app.main import app


def test_conversation_ai_flags_out_of_scope_message():
    client = TestClient(app)
    response = client.post("/ai/reply", json={
        "contact_id": "ct_123",
        "message": "Je veux un appel individuel avant de payer"
    })
    assert response.status_code == 200
    body = response.json()
    assert "reply" in body
    assert "needs_human" in body


def test_conversation_ai_handles_financial_objection():
    client = TestClient(app)
    response = client.post("/ai/reply", json={
        "contact_id": "ct_456",
        "message": "C'est trop cher pour moi"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["needs_human"] is True
    assert "reply" in body


def test_conversation_ai_handles_faq():
    client = TestClient(app)
    response = client.post("/ai/reply", json={
        "contact_id": "ct_789",
        "message": "Quand est-ce que cela commence ?"
    })
    assert response.status_code == 200
    body = response.json()
    assert "reply" in body
