CANDIDATE_REGISTRY: list[dict] = []


def register_candidate(candidate_id: str, candidate_type: str, score: float, recommended: bool) -> None:
    CANDIDATE_REGISTRY.append({
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "score": score,
        "recommended": recommended,
        "status": "pending_human_review",
    })


def list_candidates() -> list[dict]:
    return CANDIDATE_REGISTRY
