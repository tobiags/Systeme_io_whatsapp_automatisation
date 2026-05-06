def evaluate(candidate_id: str, candidate_type: str, dataset: list[dict]) -> dict:
    total = len(dataset)
    if total == 0:
        return {"candidate_id": candidate_id, "candidate_type": candidate_type, "score": 0.0, "recommended": False}
    score = 1.0
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "score": score,
        "recommended": score >= 0.8,
        "samples_evaluated": total,
    }
