# Plan d'implementation de la plateforme d'engagement WhatsApp

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** construire une plateforme WhatsApp industrialisable pour engagement, scoring, segmentation, relances automatisees, IA conversationnelle et dashboard operateur.

**Architecture:** monorepo modulaire par domaines avec services FastAPI, PostgreSQL comme source de verite, Redis + workers pour l'asynchrone, n8n limite aux integrations, dashboard web separe, et contrats explicites entre modules pour permettre une delegation par LLM.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, Pydantic, React, TypeScript, Vite, n8n, Docker Compose, pytest.

---

## Structure cible

Le code doit etre organise ainsi des le depart :

```text
platform/
  services/
    api-gateway/
    contacts/
    consent/
    campaigns/
    messaging/
    scoring/
    segmentation/
    conversation-ai/
    integrations/
    dashboard-api/
    observability/
    improvement-lab/
  apps/
    admin-console/
  shared/
    contracts/
    events/
    auth/
    config/
    db/
    testing/
  infra/
    docker/
    nginx/
    n8n/
    scripts/
    backups/
    monitoring/
  docs/
    architecture/
    modules/
    runbooks/
  tests/
    contract/
    e2e/
```

## Hypotheses de planification

- le projet demarre dans un nouveau repository
- l'implementation commence en monorepo modulaire
- chaque domaine peut ensuite etre confie a un LLM ou une equipe distincte
- le provider WhatsApp est abstrait derriere une interface commune
- les details fonctionnels des messages J-7 a J+2 seront injectes dans le moteur de campagnes, pas codes en dur dans un provider
- le programme s'appelle `Challenge Amazon FBA`
- chaque edition du challenge dure `3 jours`, du `jeudi au samedi`
- le challenge a lieu `2 fois par mois`
- deux cohortes horaires sont a gerer : `EU` et `US/CA`
- les liens `StreamYard` changent a chaque edition
- la base d'inscrits est majoritairement debutante
- les objections principales a traiter dans les parcours et la conversation sont financieres

---

### Tache 1: Initialiser le monorepo et l'infrastructure locale

**Files:**
- Create: `platform/pyproject.toml`
- Create: `platform/.env.example`
- Create: `platform/docker-compose.yml`
- Create: `platform/Makefile`
- Create: `platform/README.md`
- Create: `platform/shared/config/settings.py`
- Create: `platform/shared/db/base.py`
- Create: `platform/shared/testing/conftest.py`
- Create: `platform/infra/docker/postgres.Dockerfile`
- Create: `platform/infra/docker/api.Dockerfile`
- Test: `platform/tests/e2e/test_stack_boot.py`

- [ ] **Step 1: Ecrire le test d'amorcage de stack**

```python
from pathlib import Path


def test_stack_layout_exists():
    root = Path(__file__).resolve().parents[2]
    assert (root / "docker-compose.yml").exists()
    assert (root / "shared" / "config" / "settings.py").exists()
    assert (root / ".env.example").exists()
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_stack_boot.py -v`
Expected: FAIL with missing files under `platform/`

- [ ] **Step 3: Ecrire l'ossature minimale**

```toml
[project]
name = "whatsapp-engagement-platform"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "sqlalchemy",
  "alembic",
  "psycopg[binary]",
  "redis",
  "celery",
  "pydantic-settings",
  "httpx"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "whatsapp-engagement-platform"
    environment: str = "local"
    postgres_dsn: str = "postgresql+psycopg://app:app@postgres:5432/app"
    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    ports:
      - "5432:5432"
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_stack_boot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git init
git add platform
git commit -m "chore: initialize monorepo and local infrastructure"
```

---

### Tache 2: Poser le socle partage et les contrats transverses

**Files:**
- Create: `platform/shared/contracts/contact.py`
- Create: `platform/shared/contracts/events.py`
- Create: `platform/shared/contracts/message.py`
- Create: `platform/shared/auth/security.py`
- Create: `platform/shared/db/models.py`
- Create: `platform/shared/events/bus.py`
- Create: `platform/tests/contract/test_shared_contracts.py`

- [ ] **Step 1: Ecrire les tests de contrat de base**

```python
from shared.contracts.contact import ContactUpsert
from shared.contracts.events import DomainEvent


def test_contact_upsert_contract():
    payload = ContactUpsert(phone="+22900000000", first_name="Ada", source="systemeio")
    assert payload.phone.startswith("+")
    assert payload.source == "systemeio"


def test_domain_event_contract():
    event = DomainEvent(name="contact.created", aggregate_id="c_123", payload={"source": "systemeio"})
    assert event.name == "contact.created"
```

- [ ] **Step 2: Lancer les tests de contrat et verifier qu'ils echouent**

Run: `pytest platform/tests/contract/test_shared_contracts.py -v`
Expected: FAIL because shared contracts are missing

- [ ] **Step 3: Ecrire les contrats minimaux**

```python
from pydantic import BaseModel


class ContactUpsert(BaseModel):
    phone: str
    first_name: str | None = None
    source: str
```

```python
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    name: str
    aggregate_id: str
    payload: dict
    version: int = Field(default=1)
```

```python
from pydantic import BaseModel


class OutboundMessage(BaseModel):
    contact_id: str
    channel: str = "whatsapp"
    template_key: str
    variables: dict[str, str]
```

- [ ] **Step 4: Relancer les tests**

Run: `pytest platform/tests/contract/test_shared_contracts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/shared platform/tests/contract/test_shared_contracts.py
git commit -m "feat: add shared contracts and foundational domain types"
```

---

### Tache 3: Implementer Contacts et Consentement

**Files:**
- Create: `platform/services/contacts/app/main.py`
- Create: `platform/services/contacts/app/models.py`
- Create: `platform/services/contacts/app/repository.py`
- Create: `platform/services/contacts/app/service.py`
- Create: `platform/services/consent/app/main.py`
- Create: `platform/services/consent/app/models.py`
- Create: `platform/services/consent/app/service.py`
- Create: `platform/tests/e2e/test_contacts_and_consent.py`

- [ ] **Step 1: Ecrire le test de creation contact + validation consentement**

```python
from fastapi.testclient import TestClient

from services.contacts.app.main import app as contacts_app
from services.consent.app.main import app as consent_app


def test_create_contact_then_check_eligibility():
    contact_client = TestClient(contacts_app)
    consent_client = TestClient(consent_app)

    response = contact_client.post("/contacts", json={
        "phone": "+22900000000",
        "first_name": "Ada",
        "source": "systemeio"
    })
    assert response.status_code == 201
    contact_id = response.json()["id"]

    optin = consent_client.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "landing_page"
    })
    assert optin.status_code == 201

    eligibility = consent_client.get(f"/consents/{contact_id}/eligibility")
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_contacts_and_consent.py -v`
Expected: FAIL because service apps and routes do not exist

- [ ] **Step 3: Ecrire l'implementation minimale**

```python
from fastapi import FastAPI, status
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI()
_CONTACTS: dict[str, dict] = {}


class CreateContact(BaseModel):
    phone: str
    first_name: str | None = None
    source: str


@app.post("/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(payload: CreateContact):
    contact_id = f"ct_{uuid4().hex[:8]}"
    data = {"id": contact_id, **payload.model_dump()}
    _CONTACTS[contact_id] = data
    return data
```

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()
_CONSENTS: dict[str, dict] = {}


class CreateConsent(BaseModel):
    contact_id: str
    status: str
    proof_source: str


@app.post("/consents", status_code=status.HTTP_201_CREATED)
def create_consent(payload: CreateConsent):
    _CONSENTS[payload.contact_id] = payload.model_dump()
    return payload.model_dump()


@app.get("/consents/{contact_id}/eligibility")
def get_eligibility(contact_id: str):
    consent = _CONSENTS.get(contact_id)
    return {"contact_id": contact_id, "eligible": bool(consent and consent["status"] == "opted_in")}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_contacts_and_consent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/contacts platform/services/consent platform/tests/e2e/test_contacts_and_consent.py
git commit -m "feat: add contacts and consent services"
```

---

### Tache 4: Implementer Messaging Delivery et abstraction fournisseur

**Files:**
- Create: `platform/services/messaging/app/main.py`
- Create: `platform/services/messaging/app/providers/base.py`
- Create: `platform/services/messaging/app/providers/wati.py`
- Create: `platform/services/messaging/app/providers/dialog360.py`
- Create: `platform/services/messaging/app/service.py`
- Create: `platform/tests/e2e/test_messaging_delivery.py`

- [ ] **Step 1: Ecrire le test d'envoi via provider abstrait**

```python
from fastapi.testclient import TestClient

from services.messaging.app.main import app


def test_send_message_returns_delivery_record():
    client = TestClient(app)
    response = client.post("/messages/send", json={
        "contact_id": "ct_123",
        "template_key": "welcome_j7",
        "variables": {"first_name": "Ada"}
    })
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["provider"] in {"wati", "360dialog", "mock"}
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_messaging_delivery.py -v`
Expected: FAIL because messaging service does not exist

- [ ] **Step 3: Ecrire le provider minimal et l'endpoint**

```python
from abc import ABC, abstractmethod


class MessagingProvider(ABC):
    @abstractmethod
    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        raise NotImplementedError
```

```python
from .base import MessagingProvider


class MockProvider(MessagingProvider):
    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        return {
            "provider": "mock",
            "provider_message_id": f"msg_{contact_id}",
            "status": "queued",
            "template_key": template_key,
        }
```

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

from services.messaging.app.providers.wati import MockProvider

app = FastAPI()
provider = MockProvider()


class SendMessageRequest(BaseModel):
    contact_id: str
    template_key: str
    variables: dict[str, str]


@app.post("/messages/send", status_code=status.HTTP_202_ACCEPTED)
def send_message(payload: SendMessageRequest):
    return provider.send_template(payload.contact_id, payload.template_key, payload.variables)
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_messaging_delivery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/messaging platform/tests/e2e/test_messaging_delivery.py
git commit -m "feat: add messaging delivery service and provider abstraction"
```

---

### Tache 5: Implementer Campagnes et ordonnanceur

**Files:**
- Create: `platform/services/campaigns/app/main.py`
- Create: `platform/services/campaigns/app/models.py`
- Create: `platform/services/campaigns/app/rules.py`
- Create: `platform/services/campaigns/app/scheduler.py`
- Create: `platform/services/campaigns/app/workers.py`
- Create: `platform/services/campaigns/app/challenge_calendar.py`
- Test: `platform/tests/e2e/test_campaign_enrollment.py`

- [ ] **Step 1: Ecrire le test d'inscription dans une sequence**

```python
from fastapi.testclient import TestClient

from services.campaigns.app.main import app


def test_enroll_contact_into_journey_creates_first_scheduled_step():
    client = TestClient(app)
    response = client.post("/campaigns/enroll", json={
        "contact_id": "ct_123",
        "campaign_key": "challenge-amazon-fba",
        "region": "EU"
    })
    assert response.status_code == 201
    body = response.json()
    assert body["campaign_key"] == "challenge-amazon-fba"
    assert body["cohort"] == "EU"
    assert body["next_step"]["step_key"] == "J-7"
    assert body["live_timezone"] == "Europe"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_campaign_enrollment.py -v`
Expected: FAIL because campaign engine is missing

- [ ] **Step 3: Ecrire le moteur minimal**

```python
from dataclasses import dataclass


@dataclass
class JourneyStep:
    step_key: str
    template_key: str


DEFAULT_JOURNEY = [
    JourneyStep(step_key="J-7", template_key="welcome_j7"),
    JourneyStep(step_key="J-6", template_key="content_j6"),
    JourneyStep(step_key="DAY_1", template_key="challenge_day_1"),
    JourneyStep(step_key="DAY_2", template_key="challenge_day_2"),
    JourneyStep(step_key="DAY_3", template_key="challenge_day_3"),
]
```

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

from services.campaigns.app.rules import DEFAULT_JOURNEY

app = FastAPI()


class EnrollRequest(BaseModel):
    contact_id: str
    campaign_key: str
    region: str


@app.post("/campaigns/enroll", status_code=status.HTTP_201_CREATED)
def enroll_contact(payload: EnrollRequest):
    next_step = DEFAULT_JOURNEY[0]
    live_timezone = "Europe" if payload.region == "EU" else "America/Montreal"
    return {
        "contact_id": payload.contact_id,
        "campaign_key": payload.campaign_key,
        "cohort": payload.region,
        "live_timezone": live_timezone,
        "next_step": {"step_key": next_step.step_key, "template_key": next_step.template_key},
    }
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_campaign_enrollment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/campaigns platform/tests/e2e/test_campaign_enrollment.py
git commit -m "feat: add campaign engine and workflow scheduler skeleton"
```

---

### Tache 6: Implementer Scoring et Segmentation

**Files:**
- Create: `platform/services/scoring/app/main.py`
- Create: `platform/services/scoring/app/rules.py`
- Create: `platform/services/segmentation/app/main.py`
- Create: `platform/services/segmentation/app/service.py`
- Test: `platform/tests/e2e/test_scoring_segmentation.py`

- [ ] **Step 1: Ecrire le test de calcul de score et segment**

```python
from fastapi.testclient import TestClient

from services.scoring.app.main import app as scoring_app
from services.segmentation.app.main import app as segmentation_app


def test_score_maps_to_expected_segment():
    scoring = TestClient(scoring_app)
    segmentation = TestClient(segmentation_app)

    score_response = scoring.post("/scores/calculate", json={
        "contact_id": "ct_123",
        "events": ["registered", "opened_message", "confirmed_live"]
    })
    assert score_response.status_code == 200
    score = score_response.json()["score"]

    segment_response = segmentation.post("/segments/assign", json={
        "contact_id": "ct_123",
        "score": score
    })
    assert segment_response.status_code == 200
    assert segment_response.json()["segment"] in {"froid", "tiede", "chaud", "tres_chaud"}
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_scoring_segmentation.py -v`
Expected: FAIL because scoring and segmentation services do not exist

- [ ] **Step 3: Ecrire les regles minimales**

```python
SCORE_RULES = {
    "registered": 10,
    "opened_message": 5,
    "clicked_link": 10,
    "confirmed_live": 30,
    "asked_question": 20,
    "paid_offer": 50,
}
```

```python
from fastapi import FastAPI
from pydantic import BaseModel

from services.scoring.app.rules import SCORE_RULES

app = FastAPI()


class ScoreRequest(BaseModel):
    contact_id: str
    events: list[str]


@app.post("/scores/calculate")
def calculate_score(payload: ScoreRequest):
    score = sum(SCORE_RULES.get(event, 0) for event in payload.events)
    return {"contact_id": payload.contact_id, "score": score}
```

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class SegmentRequest(BaseModel):
    contact_id: str
    score: int


@app.post("/segments/assign")
def assign_segment(payload: SegmentRequest):
    score = payload.score
    if score <= 20:
        segment = "froid"
    elif score <= 50:
        segment = "tiede"
    elif score <= 80:
        segment = "chaud"
    else:
        segment = "tres_chaud"
    return {"contact_id": payload.contact_id, "segment": segment}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_scoring_segmentation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/scoring platform/services/segmentation platform/tests/e2e/test_scoring_segmentation.py
git commit -m "feat: add scoring and segmentation services"
```

---

### Tache 7: Implementer les connecteurs d'integrations

**Files:**
- Create: `platform/services/integrations/app/main.py`
- Create: `platform/services/integrations/app/connectors/systemeio.py`
- Create: `platform/services/integrations/app/connectors/stripe.py`
- Create: `platform/services/integrations/app/connectors/streamyard.py`
- Create: `platform/services/integrations/app/normalizer.py`
- Test: `platform/tests/e2e/test_systemeio_webhook.py`
- Test: `platform/tests/e2e/test_streamyard_session_link.py`

- [ ] **Step 1: Ecrire le test de webhook Systeme.io**

```python
from fastapi.testclient import TestClient

from services.integrations.app.main import app


def test_systemeio_webhook_is_normalized():
    client = TestClient(app)
    response = client.post("/webhooks/systemeio", json={
        "email": "ada@example.com",
        "phone_number": "+22900000000",
        "first_name": "Ada"
    })
    assert response.status_code == 202
    body = response.json()
    assert body["event_name"] == "lead.captured"
    assert body["payload"]["phone"] == "+22900000000"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_systemeio_webhook.py -v`
Expected: FAIL because integration service is missing

- [ ] **Step 3: Ecrire la normalisation minimale**

```python
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
```

```python
from fastapi import FastAPI, status

from services.integrations.app.normalizer import normalize_systemeio

app = FastAPI()


@app.post("/webhooks/systemeio", status_code=status.HTTP_202_ACCEPTED)
def systemeio_webhook(payload: dict):
    return normalize_systemeio(payload)
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_systemeio_webhook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/integrations platform/tests/e2e/test_systemeio_webhook.py
git commit -m "feat: add integration hub and Systeme.io webhook normalization"
```

- [ ] **Step 6: Ecrire le test du lien de session StreamYard**

```python
from fastapi.testclient import TestClient

from services.integrations.app.main import app


def test_streamyard_link_is_bound_to_challenge_edition():
    client = TestClient(app)
    response = client.post("/webhooks/streamyard/session", json={
        "challenge_key": "challenge-amazon-fba",
        "edition_key": "2026-05-07-eu",
        "region": "EU",
        "join_url": "https://streamyard.com/example"
    })
    assert response.status_code == 202
    assert response.json()["edition_key"] == "2026-05-07-eu"
    assert response.json()["join_url"] == "https://streamyard.com/example"
```

- [ ] **Step 7: Implementer la route minimale StreamYard**

```python
@app.post("/webhooks/streamyard/session", status_code=status.HTTP_202_ACCEPTED)
def streamyard_session(payload: dict):
    return {
        "challenge_key": payload.get("challenge_key"),
        "edition_key": payload.get("edition_key"),
        "region": payload.get("region"),
        "join_url": payload.get("join_url"),
    }
```

- [ ] **Step 8: Lancer les deux tests d'integration**

Run: `pytest platform/tests/e2e/test_systemeio_webhook.py platform/tests/e2e/test_streamyard_session_link.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add platform/services/integrations platform/tests/e2e/test_systemeio_webhook.py platform/tests/e2e/test_streamyard_session_link.py
git commit -m "feat: add StreamYard session link ingestion per challenge edition"
```

---

### Tache 8: Implementer Dashboard API, read models et console admin

**Files:**
- Create: `platform/services/dashboard-api/app/main.py`
- Create: `platform/services/dashboard-api/app/read_models.py`
- Create: `platform/apps/admin-console/package.json`
- Create: `platform/apps/admin-console/src/main.tsx`
- Create: `platform/apps/admin-console/src/App.tsx`
- Create: `platform/apps/admin-console/src/features/overview/OverviewPage.tsx`
- Create: `platform/tests/e2e/test_dashboard_summary.py`

- [ ] **Step 1: Ecrire le test de synthese dashboard**

```python
from fastapi.testclient import TestClient

from services.dashboard-api.app.main import app


def test_dashboard_summary_endpoint_returns_kpis():
    client = TestClient(app)
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    body = response.json()
    assert "contacts_total" in body
    assert "campaigns_active" in body
    assert "manual_followups" in body
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_dashboard_summary.py -v`
Expected: FAIL because dashboard API does not exist

- [ ] **Step 3: Ecrire l'API et l'UI minimale**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/dashboard/summary")
def dashboard_summary():
    return {
        "contacts_total": 0,
        "campaigns_active": 0,
        "manual_followups": 0,
        "conversion_rate": 0.0,
    }
```

```json
{
  "name": "admin-console",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10"
  }
}
```

```tsx
export default function App() {
  return (
    <main>
      <h1>Dashboard engagement WhatsApp</h1>
      <p>Vue operateur initiale</p>
    </main>
  );
}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_dashboard_summary.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/dashboard-api platform/apps/admin-console platform/tests/e2e/test_dashboard_summary.py
git commit -m "feat: add dashboard api and admin console shell"
```

---

### Tache 9: Implementer IA conversationnelle et escalade humaine

**Files:**
- Create: `platform/services/conversation-ai/app/main.py`
- Create: `platform/services/conversation-ai/app/prompts.py`
- Create: `platform/services/conversation-ai/app/service.py`
- Create: `platform/services/conversation-ai/app/escalation.py`
- Test: `platform/tests/e2e/test_conversation_ai.py`

- [ ] **Step 1: Ecrire le test de FAQ et d'escalade**

```python
from fastapi.testclient import TestClient

from services.conversation-ai.app.main import app


def test_conversation_ai_flags_out_of_scope_message():
    client = TestClient(app)
    response = client.post("/ai/reply", json={
        "contact_id": "ct_123",
        "message": "Je veux un appel individuel avant de payer"
    })
    assert response.status_code == 200
    body = response.json()
    assert "reply" in body
    assert "needs_human" in body
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_conversation_ai.py -v`
Expected: FAIL because conversation AI service does not exist

- [ ] **Step 3: Ecrire l'encadrement minimal du service**

```python
FAQ = {
    "quand ca commence": "Le Challenge Amazon FBA se deroule du jeudi au samedi selon votre zone horaire.",
    "comment rejoindre le groupe whatsapp": "Le lien du groupe WhatsApp vous est envoye dans la sequence de bienvenue.",
    "je me suis inscrit mais je n'ai pas recu d'email": "Verifiez vos spams puis contactez le support si besoin.",
    "combien coute la formation": "Les details de l'offre sont communiques pendant et apres le challenge.",
}
```

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class AIRequest(BaseModel):
    contact_id: str
    message: str


@app.post("/ai/reply")
def ai_reply(payload: AIRequest):
    text = payload.message.lower()
    needs_human = "appel" in text or "remboursement" in text
    if "combien" in text or "cher" in text or "prix" in text or "budget" in text:
        reply = "Je comprends votre question sur le budget. Le challenge est gratuit et les details de la formation sont presentes pendant le parcours."
    elif needs_human:
        reply = "Je transmets votre demande a un conseiller."
    else:
        reply = "Merci pour votre message. Voici la reponse la plus adaptee pour vous aider a bien demarrer."
    return {"contact_id": payload.contact_id, "reply": reply, "needs_human": needs_human}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_conversation_ai.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/conversation-ai platform/tests/e2e/test_conversation_ai.py
git commit -m "feat: add bounded conversation ai service and escalation flagging"
```

---

### Tache 10: Implementer observabilite, audit et journaux

**Files:**
- Create: `platform/services/observability/app/main.py`
- Create: `platform/services/observability/app/logging.py`
- Create: `platform/services/observability/app/audit.py`
- Create: `platform/shared/events/store.py`
- Test: `platform/tests/e2e/test_audit_log.py`

- [ ] **Step 1: Ecrire le test de journal d'audit**

```python
from fastapi.testclient import TestClient

from services.observability.app.main import app


def test_audit_log_accepts_event():
    client = TestClient(app)
    response = client.post("/audit/events", json={
        "name": "message.sent",
        "aggregate_id": "ct_123",
        "payload": {"template_key": "welcome_j7"}
    })
    assert response.status_code == 201
    assert response.json()["name"] == "message.sent"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_audit_log.py -v`
Expected: FAIL because observability service is missing

- [ ] **Step 3: Ecrire l'endpoint minimal**

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()
AUDIT_LOG: list[dict] = []


class AuditEvent(BaseModel):
    name: str
    aggregate_id: str
    payload: dict


@app.post("/audit/events", status_code=status.HTTP_201_CREATED)
def create_audit_event(payload: AuditEvent):
    event = payload.model_dump()
    AUDIT_LOG.append(event)
    return event
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_audit_log.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/observability platform/shared/events/store.py platform/tests/e2e/test_audit_log.py
git commit -m "feat: add observability and audit service"
```

---

### Tache 11: Implementer le Continuous Improvement Lab

**Files:**
- Create: `platform/services/improvement-lab/app/main.py`
- Create: `platform/services/improvement-lab/app/datasets.py`
- Create: `platform/services/improvement-lab/app/evaluators.py`
- Create: `platform/services/improvement-lab/app/registry.py`
- Create: `platform/docs/modules/improvement-lab.md`
- Test: `platform/tests/e2e/test_improvement_lab.py`

- [ ] **Step 1: Ecrire le test d'evaluation offline**

```python
from fastapi.testclient import TestClient

from services.improvement-lab.app.main import app


def test_improvement_lab_scores_candidate_prompt():
    client = TestClient(app)
    response = client.post("/lab/evaluate", json={
        "candidate_id": "prompt_v2",
        "candidate_type": "prompt",
        "dataset": [
            {"input": "C'est quand le live ?", "expected_intent": "faq_schedule"},
            {"input": "Je veux un appel", "expected_intent": "human_escalation"}
        ]
    })
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"] == "prompt_v2"
    assert "score" in body
    assert "recommended" in body
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_improvement_lab.py -v`
Expected: FAIL because improvement lab service does not exist

- [ ] **Step 3: Ecrire le service minimal**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class EvaluationRequest(BaseModel):
    candidate_id: str
    candidate_type: str
    dataset: list[dict]


@app.post("/lab/evaluate")
def evaluate_candidate(payload: EvaluationRequest):
    total = len(payload.dataset)
    score = 1.0 if total else 0.0
    return {
        "candidate_id": payload.candidate_id,
        "candidate_type": payload.candidate_type,
        "score": score,
        "recommended": score >= 0.8,
    }
```

```markdown
# Improvement Lab

Ce module execute des evaluations offline inspirees d'une boucle de type autoresearch.

Il ne pousse jamais directement en production.

Il sert a :

- comparer variantes de prompts
- evaluer heuristiques de classification
- scorer des candidats de reponse
- produire des recommandations de promotion
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_improvement_lab.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/improvement-lab platform/docs/modules/improvement-lab.md platform/tests/e2e/test_improvement_lab.py
git commit -m "feat: add continuous improvement lab for offline evaluations"
```

---

### Tache 12: Integrer API Gateway et contrats inter-services

**Files:**
- Create: `platform/services/api-gateway/app/main.py`
- Create: `platform/services/api-gateway/app/routes.py`
- Create: `platform/tests/contract/test_gateway_routes.py`

- [ ] **Step 1: Ecrire le test de route de facade**

```python
from fastapi.testclient import TestClient

from services.api-gateway.app.main import app


def test_gateway_health_route():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_gateway_routes.py -v`
Expected: FAIL because gateway service is missing

- [ ] **Step 3: Ecrire le gateway minimal**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_gateway_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/services/api-gateway platform/tests/contract/test_gateway_routes.py
git commit -m "feat: add api gateway shell"
```

---

### Tache 13: Finaliser la chaine E2E, le deploiement et les runbooks

**Files:**
- Create: `platform/tests/e2e/test_lead_to_segment_flow.py`
- Create: `platform/infra/nginx/default.conf`
- Create: `platform/infra/n8n/README.md`
- Create: `platform/docs/runbooks/deployment.md`
- Create: `platform/docs/runbooks/replay-failed-message.md`
- Create: `platform/docs/modules/ownership-matrix.md`

- [ ] **Step 1: Ecrire le test de flux principal**

```python
from fastapi.testclient import TestClient

from services.contacts.app.main import app as contacts_app
from services.consent.app.main import app as consent_app
from services.campaigns.app.main import app as campaigns_app
from services.messaging.app.main import app as messaging_app
from services.scoring.app.main import app as scoring_app
from services.segmentation.app.main import app as segmentation_app


def test_lead_to_segment_flow():
    contacts = TestClient(contacts_app)
    consent = TestClient(consent_app)
    campaigns = TestClient(campaigns_app)
    messaging = TestClient(messaging_app)
    scoring = TestClient(scoring_app)
    segmentation = TestClient(segmentation_app)

    created = contacts.post("/contacts", json={
        "phone": "+22900000000",
        "first_name": "Ada",
        "source": "systemeio"
    })
    assert created.status_code == 201
    contact_id = created.json()["id"]

    approved = consent.post("/consents", json={
        "contact_id": contact_id,
        "status": "opted_in",
        "proof_source": "landing_page"
    })
    assert approved.status_code == 201

    enrolled = campaigns.post("/campaigns/enroll", json={
        "contact_id": contact_id,
        "campaign_key": "amazon-fba-live"
    })
    assert enrolled.status_code == 201
    template_key = enrolled.json()["next_step"]["template_key"]

    sent = messaging.post("/messages/send", json={
        "contact_id": contact_id,
        "template_key": template_key,
        "variables": {"first_name": "Ada"}
    })
    assert sent.status_code == 202

    score = scoring.post("/scores/calculate", json={
        "contact_id": contact_id,
        "events": ["registered", "opened_message", "confirmed_live"]
    })
    assert score.status_code == 200

    segment = segmentation.post("/segments/assign", json={
        "contact_id": contact_id,
        "score": score.json()["score"]
    })
    assert segment.status_code == 200
    assert segment.json()["segment"] == "chaud"
```

- [ ] **Step 2: Lancer le test et verifier l'etat initial**

Run: `pytest platform/tests/e2e/test_lead_to_segment_flow.py -v`
Expected: FAIL until all dependent services are wired and executable together

- [ ] **Step 3: Ecrire les artefacts de delivery**

```nginx
server {
  listen 80;
  server_name _;

  location /api/ {
    proxy_pass http://api-gateway:8000/;
  }

  location / {
    proxy_pass http://admin-console:5173/;
  }
}
```

```markdown
# Deploiement

1. Renseigner `.env`
2. Demarrer `docker compose up -d`
3. Executer les migrations
4. Verifier `/health`
5. Verifier les webhooks provider
```

```markdown
# Matrice d'ownership

- LLM-1 : Platform Core
- LLM-2 : Contacts et conformite
- LLM-3 : Campagnes et automation
- LLM-4 : Messaging
- LLM-5 : Scoring et segmentation
- LLM-6 : IA conversationnelle
- LLM-7 : Integrations
- LLM-8 : Dashboard
- LLM-9 : Observabilite
```

- [ ] **Step 4: Lancer la suite minimale de verification**

Run: `pytest platform/tests/contract platform/tests/e2e -v`
Expected: PASS on all contract and end-to-end tests, including `test_lead_to_segment_flow`

- [ ] **Step 5: Commit**

```bash
git add platform/tests/e2e/test_lead_to_segment_flow.py platform/infra platform/docs
git commit -m "docs: add deployment runbooks and ownership matrix"
```

---

## Sequence d'execution recommandee par LLM

1. `LLM-1` execute les Taches 1, 2 et 11
2. `LLM-2` execute la Tache 3
3. `LLM-4` execute la Tache 4
4. `LLM-3` execute la Tache 5
5. `LLM-5` execute la Tache 6
6. `LLM-7` execute la Tache 7
7. `LLM-8` execute la Tache 8
8. `LLM-6` execute la Tache 9
9. `LLM-9` execute la Tache 10
10. `LLM-6` ou `LLM-9` execute la Tache 11
11. `LLM-1` execute la Tache 12
12. `LLM-1` ou `Lead Integrator` execute la Tache 13

## Points de controle entre taches

- apres Tache 3 : schema contact + consentement valide
- apres Tache 4 : abstraction provider stable
- apres Tache 5 : structure des campagnes J-7 a J+2 figee
- apres Tache 6 : barreme scoring et mapping segment valides
- apres Tache 7 : format des webhooks normalises fige
- apres Tache 8 : KPI operateur et vues prioritaires valides
- apres Tache 9 : garde-fous conversation IA valides
- apres Tache 10 : audit trail et logs structures operationnels
- apres Tache 11 : boucle d'amelioration offline bornee et gouvernee
- apres Tache 13 : flux critique et runbooks valides

## Risques a surveiller pendant l'execution

- laisser n8n porter de la logique metier critique
- laisser le LLM modifier des verites metier officielles
- coupler directement le dashboard aux tables transactionnelles
- ne pas versionner les regles de scoring et de segmentation
- ne pas rendre les webhooks idempotents
- ne pas tracer les retries et echecs provider
- laisser une boucle autoresearch toucher la prod sans validation humaine

## Definition of done du projet

- tous les domaines critiques existent en modules separes
- les contrats inter-modules sont documentes et testes
- le flux lead -> contact -> consentement -> campagne -> message -> score -> segment -> dashboard fonctionne
- l'IA conversationnelle reste bornee et escalade correctement
- les integrations externes sont normalisees
- les dashboards operateurs couvrent supervision et relances
- l'observabilite permet audit, replay et diagnostic
- le continuous improvement lab evalue offline prompts et heuristiques avant promotion
- les runbooks de deploiement et reprise sont ecrits
