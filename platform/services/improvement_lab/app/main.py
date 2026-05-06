from fastapi import FastAPI
from pydantic import BaseModel

from services.improvement_lab.app.evaluators import evaluate
from services.improvement_lab.app.registry import list_candidates, register_candidate

app = FastAPI()


class EvaluationRequest(BaseModel):
    candidate_id: str
    candidate_type: str
    dataset: list[dict]


@app.post("/lab/evaluate")
def evaluate_candidate(payload: EvaluationRequest):
    result = evaluate(payload.candidate_id, payload.candidate_type, payload.dataset)
    register_candidate(
        payload.candidate_id,
        payload.candidate_type,
        result["score"],
        result["recommended"],
    )
    return result


@app.get("/lab/candidates")
def get_candidates():
    return list_candidates()
