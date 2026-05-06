from fastapi.testclient import TestClient

from services.scoring.app.main import app as scoring_app
from services.segmentation.app.main import app as segmentation_app


def test_score_maps_to_expected_segment():
    scoring = TestClient(scoring_app)
    segmentation = TestClient(segmentation_app)

    score_response = scoring.post("/scores/calculate", json={
        "contact_id": "ct_123",
        "events": ["registered", "opened_message", "confirmed_live"]
    })
    assert score_response.status_code == 200
    score = score_response.json()["score"]

    segment_response = segmentation.post("/segments/assign", json={
        "contact_id": "ct_123",
        "score": score
    })
    assert segment_response.status_code == 200
    assert segment_response.json()["segment"] in {"froid", "tiede", "chaud", "tres_chaud"}
