from services.integrations.app.normalizer import normalize_systemeio


def handle_webhook(payload: dict) -> dict:
    return normalize_systemeio(payload)
