def handle_session(payload: dict) -> dict:
    return {
        "challenge_key": payload.get("challenge_key"),
        "edition_key": payload.get("edition_key"),
        "region": payload.get("region"),
        "join_url": payload.get("join_url"),
    }
