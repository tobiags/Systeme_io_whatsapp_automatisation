def handle_webhook(payload: dict) -> dict:
    return {
        "event_name": "payment.received",
        "payload": {
            "email": payload.get("email"),
            "amount": payload.get("amount"),
            "currency": payload.get("currency"),
            "source": "stripe",
        },
    }
