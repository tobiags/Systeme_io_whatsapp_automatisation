import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shared.db.base import Base
from shared.config.settings import settings
from shared.db.session import get_db

from services.api_gateway.app.main import app as gateway_app
from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.contacts.app.main import app as contacts_app
from services.conversation_ai.app.main import app as ai_app
from services.dashboard_api.app.main import app as dashboard_app
from services.improvement_lab.app.main import app as lab_app
from services.integrations.app.main import app as integrations_app
from services.messaging.app.main import app as messaging_app
from services.observability.app.main import app as observability_app
from services.scoring.app.main import app as scoring_app
from services.segmentation.app.main import app as segmentation_app

_ALL_APPS = [
    gateway_app, campaigns_app, consent_app, contacts_app, ai_app, dashboard_app,
    integrations_app, lab_app, messaging_app, observability_app, scoring_app, segmentation_app,
]

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

Base.metadata.create_all(bind=_engine)

settings.whatsapp_auto_reply_enabled = True


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


for _app in _ALL_APPS:
    _app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
