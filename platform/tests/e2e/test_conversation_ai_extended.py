"""Tests for granular FAQ intents and financial objection classification."""
from fastapi.testclient import TestClient

from services.conversation_ai.app import service
from services.conversation_ai.app.main import app
from shared.config.settings import settings

client = TestClient(app)


def test_best_skill_is_injected_into_openai_system_prompt():
    service._load_best_skill.cache_clear()
    prompt = service._build_openai_system_prompt()
    assert "Best Skill - Assistant WhatsApp Challenge Amazon FBA" in prompt
    assert "dernier message envoye" in prompt


def test_known_contact_context_uses_openai_before_generic_local_reply(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")
    captured = {}

    def fake_openai_reply(message, api_key, context=None):
        captured["message"] = message
        captured["api_key"] = api_key
        captured["context"] = context
        return {
            "reply": "Bien recu, on se retrouve sur le live du jour.",
            "needs_human": False,
            "intent": "ai_generated",
        }

    monkeypatch.setattr(service, "_openai_reply", fake_openai_reply)

    result = service.build_reply(
        "Merci",
        context={
            "contact_id": "ct_known",
            "current_step": "DAY_2",
            "edition_key": "2026-05-28-usca",
            "last_outbound_template": "live_day2_not_registered",
        },
    )

    assert result["intent"] == "ai_generated"
    assert captured["api_key"] == "test-openai-key"
    assert captured["context"]["current_step"] == "DAY_2"


def test_critical_guardrail_blocks_openai_for_price_questions(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")

    def fail_openai_reply(*args, **kwargs):
        raise AssertionError("OpenAI should not be called for price guardrails")

    monkeypatch.setattr(service, "_openai_reply", fail_openai_reply)

    result = service.build_reply(
        "Combien coute la formation ?",
        context={"contact_id": "ct_known", "current_step": "DAY_3"},
    )

    assert result["needs_human"] is True
    assert result["intent"] == "human_escalation"


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


def test_challenge_overview_variant_maps_to_faq():
    resp = client.post("/ai/reply", json={"contact_id": "ct_2b", "message": "Ca se passe comment le challenge"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "faq_challenge_overview"


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
    assert resp.json()["intent"] == "entry_choice_beginner"
    assert resp.json()["needs_human"] is False


def test_beginner_profile_variant_not_started_yet():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "Je n'ai pas encore commence"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_beginner"


def test_beginner_profile_single_zero_variant():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "0"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_beginner"


def test_beginner_profile_single_word_zero_variant():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "Zero"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_beginner"


def test_beginner_profile_leetspeak_zero_variant():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "De zer0"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_beginner"


def test_entry_choice_one_maps_to_beginner():
    resp = client.post("/ai/reply", json={"contact_id": "ct_entry_1", "message": "1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "entry_choice_beginner"
    assert body["needs_human"] is False
    assert "bases claires" in body["reply"].lower()


def test_entry_choice_two_maps_to_started():
    resp = client.post("/ai/reply", json={"contact_id": "ct_entry_2", "message": "2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "entry_choice_started"
    assert body["needs_human"] is False


def test_entry_choice_three_opens_challenge_question_path():
    resp = client.post("/ai/reply", json={"contact_id": "ct_entry_3", "message": "3"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "entry_choice_question"
    assert body["needs_human"] is False
    assert "pose" in body["reply"].lower()


def test_entry_free_text_none_experience_maps_to_beginner():
    resp = client.post("/ai/reply", json={"contact_id": "ct_entry_free_1", "message": "Aucune experience en vente en ligne"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_beginner"


def test_entry_free_text_existing_seller_maps_to_started():
    resp = client.post("/ai/reply", json={"contact_id": "ct_entry_free_2", "message": "Je faisais la vente en ligne et je suis en adaptation"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_started"


def test_entry_free_text_challenge_question_maps_to_question_bucket():
    resp = client.post("/ai/reply", json={"contact_id": "ct_entry_free_3", "message": "Comment se passe le challenge ?"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_question"


def test_started_profile_intent():
    resp = client.post("/ai/reply", json={"contact_id": "ct_demo", "message": "J'ai deja commence a vendre en ligne"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "entry_choice_started"


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


def test_gratitude_message_stays_soft_open():
    resp = client.post("/ai/reply", json={"contact_id": "ct_12", "message": "Merci Alban. C est aussi un plaisir pour moi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "soft_open_invitation"


def test_learning_interest_opens_single_followup():
    resp = client.post("/ai/reply", json={"contact_id": "ct_13", "message": "J'aimerais apprendre"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "interest_followup_objective"


def test_live_availability_statement_gets_support_reply():
    resp = client.post("/ai/reply", json={"contact_id": "ct_14", "message": "Je ferais un maximum d effort pour ne pas rater le live meme comme je serais au boulot a cette heure la"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "availability_support"


def test_live_two_links_confusion_gets_practical_answer():
    resp = client.post("/ai/reply", json={"contact_id": "ct_15", "message": "Je vois deux lien, les deux seront utilises ou l'un ?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "live_access_time_help"
    assert "dernier lien" in body["reply"].lower()


def test_live_timezone_confusion_gets_practical_answer():
    resp = client.post("/ai/reply", json={"contact_id": "ct_16", "message": "Je vis en Haiti alors je suis perdu quant a l'heure exacte du live"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "live_access_time_help"
    assert "montreal" in body["reply"].lower()


def test_live_participation_confirmation_is_not_clarification():
    resp = client.post("/ai/reply", json={"contact_id": "ct_17", "message": "J'y serai."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "live_participation_confirmed"
    assert "connecte" in body["reply"].lower()


def test_live_participation_thanks_confirmation_is_not_soft_open():
    resp = client.post("/ai/reply", json={"contact_id": "ct_17b", "message": "Merci beaucoup je n'y manquerai pas"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "live_participation_confirmed"
    assert "n'hesite pas" not in body["reply"].lower()


def test_amazon_fba_ai_tools_question_gets_useful_answer():
    resp = client.post("/ai/reply", json={
        "contact_id": "ct_17c",
        "message": "T'as des outils d'IA qui permettent de travailler plus efficacement avec Amazon FBA ?",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "amazon_fba_ai_tools_question"
    assert "recherche produit" in body["reply"].lower()


def test_emoji_only_message_does_not_trigger_clarification():
    result = service.build_reply("👍🏽", context={"contact_id": "ct_emoji"})
    assert result["intent"] == "acknowledgement_no_reply"
    assert result["reply"] == ""
    assert result["send_reply"] is False


def test_beginner_no_question_gets_reassurance():
    resp = client.post("/ai/reply", json={"contact_id": "ct_18", "message": "C'est ma premiere fois. Je ne connais rien en e-commerce."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "beginner_reassurance_no_question"
    assert "pas besoin" in body["reply"].lower()


def test_challenge_participation_requirements_gets_answer():
    resp = client.post("/ai/reply", json={"contact_id": "ct_19", "message": "Quels seront les mesures necessaires pour participer ?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_human"] is False
    assert body["intent"] == "challenge_participation_requirements"
    assert "lien du live" in body["reply"].lower()
