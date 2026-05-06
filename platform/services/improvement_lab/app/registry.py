from sqlalchemy.orm import Session

from shared.db.models import LabEvaluation


def register_candidate(
    db: Session,
    candidate_id: str,
    candidate_type: str,
    score: float,
    recommended: bool,
) -> None:
    db.add(LabEvaluation(
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        score=score,
        recommended=recommended,
    ))
    db.commit()


def list_candidates(db: Session) -> list[dict]:
    records = db.query(LabEvaluation).order_by(LabEvaluation.id).all()
    return [
        {
            "candidate_id": r.candidate_id,
            "candidate_type": r.candidate_type,
            "score": r.score,
            "recommended": r.recommended,
            "status": r.status,
        }
        for r in records
    ]
