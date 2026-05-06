from fastapi import APIRouter, FastAPI, status

from services.integrations.app.connectors.streamyard import handle_session
from services.integrations.app.normalizer import normalize_systemeio

router = APIRouter(prefix="/webhooks")


@router.post("/systemeio", status_code=status.HTTP_202_ACCEPTED)
def systemeio_webhook(payload: dict):
    return normalize_systemeio(payload)


@router.post("/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(payload: dict):
    return handle_session(payload)


app = FastAPI()
app.include_router(router)
