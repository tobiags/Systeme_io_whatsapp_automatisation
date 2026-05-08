from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.db.session import get_db

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

# ── Auth middleware ───────────────────────────────────────────────────────────
# All endpoints require X-API-Key header when PLATFORM_API_KEY is configured.
# Exempt paths are called by external systems that cannot send our key:
#   /health          — monitoring probes
#   /webhooks/systemeio — called by Systeme.io automation
#   /webhooks/wati   — called by Wati on each inbound message (exact path only)

_PUBLIC_PATHS = {
    "/health",
    "/webhooks/systemeio",
    "/webhooks/wati",
}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Auth is disabled when no key is configured (local dev / CI).
    if not settings.platform_api_key:
        return await call_next(request)

    # Public paths bypass auth.
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    # All other paths require a valid API key.
    key = request.headers.get("X-API-Key", "")
    if key != settings.platform_api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "detail": "Missing or invalid X-API-Key header."},
        )
    return await call_next(request)


# ── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )


# ── Routers ──────────────────────────────────────────────────────────────────

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


# ── Platform routes ───────────────────────────────────────────────────────────

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check — verifies API is up and DB is reachable."""
    try:
        db.execute(sa_text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@app.get("/services")
def list_services():
    return {"services": REGISTERED_SERVICES}
