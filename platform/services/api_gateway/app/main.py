from fastapi import FastAPI

from services.api_gateway.app.routes import REGISTERED_SERVICES

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/services")
def list_services():
    return {"services": REGISTERED_SERVICES}
