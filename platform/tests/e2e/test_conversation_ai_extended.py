"""Tests for granular FAQ intents and financial objection classification."""
from fastapi.testclient import TestClient

from services.conversation_ai.app.main import app

client = TestClient(app)


# â”€â”€ FAQ intent mapping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_faq_start_time_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_1", "message": "quand ca commence ?"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "faq_start_time"
    assert resp.json()["needs_human"] is False


def test_faq_whatsapp_group_join_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_2", "message": "comment rejoindre le groupe whatsapp ?"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "faq_whatsapp_group_join"


def test_faq_email_missing_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_3", "message": "je me suis inscrit mais je n'ai pas recu d'email"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "clarification_request"


def test_faq_offer_price_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_4", "message": "combien coute la formation ?"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "human_escalation"
    assert resp.json()["needs_human"] is True


def test_faq_next_challenge_date_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_5", "message": "quand est-ce que vous referez un nouveau challenge ?"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "clarification_request"


def test_beginner_profile_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "Je pars de zero"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "restricted_beginner_profile"
    assert resp.json()["needs_human"] is False


def test_beginner_profile_variant_not_started_yet():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "Je n'ai pas encore commence"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "restricted_beginner_profile"


def test_started_profile_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "J'ai deja commence a vendre en ligne"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "restricted_started_profile"


def test_time_objection_template_reply():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "Mon plus gros frein c'est le temps"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "restricted_main_obstacle"


def test_product_choice_template_reply():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "Je ne sais pas quoi vendre"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "restricted_product_choice"


# â”€â”€ Financial objection classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_payment_failure_escalates_to_human():
    resp = client.post("/ai/reply", json={"contact_id": "ct_6", "message": "j'ai essayÃ© de payer mais je n'avais pas assez"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "payment_failure_followup_needed"
    assert body["needs_human"] is True


def test_installment_request_escalates_to_human():
    resp = client.post("/ai/reply", json={"contact_id": "ct_7", "message": "est-ce que je peux payer en plusieurs fois ?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "installment_plan_request"
    assert body["needs_human"] is True


def test_sceptic_objection_no_escalation():
    resp = client.post("/ai/reply", json={"contact_id": "ct_8", "message": "j'ai peur de perdre mon argent"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "skeptic_trust_objection"
    assert body["needs_human"] is True


def test_soft_financial_objection():
    resp = client.post("/ai/reply", json={"contact_id": "ct_9", "message": "c'est trop cher pour moi"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "objection_financial_soft"
    assert resp.json()["needs_human"] is True


def test_human_escalation_still_has_priority():
    """Escalation keywords override all other classifications."""
    resp = client.post("/ai/reply", json={"contact_id": "ct_10", "message": "je veux un appel individuel avant de payer"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is True
    assert body["intent"] == "human_escalation"


def test_complex_personal_case_escalates_to_human():
    resp = client.post("/ai/reply", json={"contact_id": "ct_11", "message": "Mon cas est un peu particulier"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is True
    assert body["intent"] == "human_escalation"
