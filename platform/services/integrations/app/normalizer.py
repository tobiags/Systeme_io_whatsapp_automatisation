def normalize_systemeio(payload: dict) -> dict:
    return {
        "event_name": "lead.captured",
        "payload": {
            "email": payload.get("email"),
            "phone": payload.get("phone_number"),
            "first_name": payload.get("first_name"),
            "source": "systemeio",
        },
    }
