from fastapi.testclient import TestClient

from services.improvement_lab.app.main import app


def test_improvement_lab_scores_candidate_prompt():
    client = TestClient(app)
    response = client.post("/lab/evaluate", json={
        "candidate_id": "prompt_v2",
        "candidate_type": "prompt",
        "dataset": [
            {"input": "C'est quand le live ?", "expected_intent": "faq_schedule"},
            {"input": "Je veux un appel", "expected_intent": "human_escalation"}
        ]
    })
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"] == "prompt_v2"
    assert "score" in body
    assert "recommended" in body


def test_improvement_lab_rejects_empty_dataset():
    client = TestClient(app)
    response = client.post("/lab/evaluate", json={
        "candidate_id": "prompt_v3",
        "candidate_type": "prompt",
        "dataset": []
    })
    assert response.status_code == 200
    assert response.json()["score"] == 0.0
    assert response.json()["recommended"] is False
