from fastapi import FastAPI, status

from services.integrations.app.connectors.streamyard import handle_session
from services.integrations.app.normalizer import normalize_systemeio

app = FastAPI()


@app.post("/webhooks/systemeio", status_code=status.HTTP_202_ACCEPTED)
def systemeio_webhook(payload: dict):
    return normalize_systemeio(payload)


@app.post("/webhooks/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(payload: dict):
    return handle_session(payload)
