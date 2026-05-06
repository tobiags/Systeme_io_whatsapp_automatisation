from fastapi import FastAPI

from services.api_gateway.app.routes import REGISTERED_SERVICES
from services.campaigns.app.main import router as campaigns_router
from services.consent.app.main import router as consent_router
from services.contacts.app.main import router as contacts_router
from services.conversation_ai.app.main import router as ai_router
from services.dashboard_api.app.main import router as dashboard_router
from services.improvement_lab.app.main import router as lab_router
from services.integrations.app.main import router as integrations_router
from services.messaging.app.main import router as messaging_router
from services.observability.app.main import router as observability_router
from services.scoring.app.main import router as scoring_router
from services.segmentation.app.main import router as segmentation_router

app = FastAPI(title="WhatsApp Engagement Platform")

app.include_router(contacts_router)
app.include_router(consent_router)
app.include_router(campaigns_router)
app.include_router(messaging_router)
app.include_router(scoring_router)
app.include_router(segmentation_router)
app.include_router(integrations_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(observability_router)
app.include_router(lab_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/services")
def list_services():
    return {"services": REGISTERED_SERVICES}
