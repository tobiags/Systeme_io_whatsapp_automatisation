from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.session import get_db
from services.improvement_lab.app.evaluators import evaluate
from services.improvement_lab.app.registry import list_candidates, register_candidate

router = APIRouter(prefix="/lab")


class EvaluationRequest(BaseModel):
    candidate_id: str
    candidate_type: str
    dataset: list[dict]


@router.post("/evaluate")
def evaluate_candidate(payload: EvaluationRequest, db: Session = Depends(get_db)):
    result = evaluate(payload.candidate_id, payload.candidate_type, payload.dataset)
    register_candidate(db, payload.candidate_id, payload.candidate_type, result["score"], result["recommended"])
    return result


@router.get("/candidates")
def get_candidates(db: Session = Depends(get_db)):
    return list_candidates(db)


app = FastAPI()
app.include_router(router)
