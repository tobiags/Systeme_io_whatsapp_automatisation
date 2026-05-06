from fastapi.testclient import TestClient

from services.campaigns.app.main import app as campaigns_app
from services.consent.app.main import app as consent_app
from services.contacts.app.main import app as contacts_app
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
        "campaign_key": "challenge-amazon-fba",
        "region": "EU"
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
