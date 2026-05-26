# Bot Entry Questionnaire And Project KB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** replace the bot's open-text first-turn behavior with a guided `1 / 2 / 3` questionnaire, project-specific knowledge-base routing, and bounded ambiguity handling so real lead conversations stop falling into clarification loops.

**Architecture:** keep the existing FastAPI services and Wati inbound flow, but add a dedicated entry-questionnaire state machine stored in message metadata, expand local KB routing ahead of OpenAI, and tighten integration-side script handling so the first turn is deterministic. Existing FAQ, escalation, and campaign delivery plumbing remain in place and are extended rather than rewritten.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/SQLite test override, local KB rules in Python, pytest e2e tests, Wati template documentation JSON/Markdown.

---

## File structure and responsibilities

- `platform/services/conversation_ai/app/knowledge_base.py`
  - source of truth for project-specific routing rules
  - add questionnaire choice mapping, free-text bucket mapping, and reformulation text
- `platform/services/conversation_ai/app/service.py`
  - normalize inbound text
  - classify numeric entry choices and project KB matches before OpenAI
  - return deterministic intents and optional `script_state`
- `platform/services/integrations/app/main.py`
  - persist questionnaire state on the welcome audit message
  - interpret inbound replies in the context of the entry questionnaire
  - reformulate once, then escalate if the lead stays off-track
- `platform/tests/e2e/test_conversation_ai_extended.py`
  - direct conversation-AI regression coverage
- `platform/tests/e2e/test_wati_inbound.py`
  - end-to-end inbound routing coverage with stored state
- `platform/tests/e2e/test_auto_enrollment.py`
  - verify the welcome audit row now carries questionnaire state metadata
- `platform/docs/wati-final/TEMPLATES-WATI-FINAL.md`
  - human-facing source of truth for the new welcome copy
- `platform/docs/wati-final/templates_wati_final.json`
  - machine-readable template text reference used by docs / handoff material
- `platform/docs/bot-guardrails-system.md`
  - update the long-term maintenance guide so future sessions know the new routing order

---

### Task 1: Lock the new behavior in failing tests first

**Files:**
- Modify: `platform/tests/e2e/test_conversation_ai_extended.py`
- Modify: `platform/tests/e2e/test_wati_inbound.py`
- Modify: `platform/tests/e2e/test_auto_enrollment.py`

- [ ] **Step 1: Add failing conversation-AI tests for numeric entry choices**

```python
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
    assert "pose moi ta question" in body["reply"].lower()
```

- [ ] **Step 2: Add failing conversation-AI tests for free-text bucket mapping**

```python
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
```

- [ ] **Step 3: Add failing inbound tests for reformulation and second-off-track escalation**

```python
def test_wati_inbound_unknown_entry_reply_rephrases_once():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000040",
        "first_name": "Issiaka",
        "email": "issiaka@test.com",
    })

    first = client.post("/webhooks/wati", json={
        "waId": "+22900000040",
        "text": "Enchante Alban",
        "eventType": "messageReceived",
    })
    assert first.status_code == 200
    body = first.json()
    assert body["intent"] == "entry_questionnaire_rephrase"
    assert body["delivery"]["status"] == "queued"
    assert "1, 2 ou 3" in body["reply"]


def test_wati_inbound_second_off_track_entry_reply_escalates():
    client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000041",
        "first_name": "Christian",
        "email": "christian@test.com",
    })

    client.post("/webhooks/wati", json={
        "waId": "+22900000041",
        "text": "Bonsoir grand frere",
        "eventType": "messageReceived",
    })
    second = client.post("/webhooks/wati", json={
        "waId": "+22900000041",
        "text": "OK c'est compris grand frere",
        "eventType": "messageReceived",
    })
    assert second.status_code == 200
    body = second.json()
    assert body["intent"] == "human_escalation"
    assert body["needs_human"] is True
    assert body["delivery"]["status"] == "awaiting_human"
```

- [ ] **Step 4: Add failing welcome metadata test**

```python
def test_first_welcome_stores_entry_questionnaire_state():
    resp = client.post("/webhooks/systemeio", json={
        "phone_number": "+22900000042",
        "first_name": "Diallo",
        "email": "diallo@test.com",
    })
    assert resp.status_code == 202

    from shared.db.models import Message
    from tests.conftest import _TestingSession

    db = _TestingSession()
    try:
        welcome = db.query(Message).filter(Message.contact_id == resp.json()["contact_id"], Message.template_key == "welcome").first()
        assert welcome is not None
        assert welcome.variables["script_state"] == {
            "flow": "entry_questionnaire",
            "stage": "awaiting_choice",
            "rephrase_count": 0,
        }
    finally:
        db.close()
```

- [ ] **Step 5: Run the focused tests to confirm they fail**

Run: `python -m pytest platform/tests/e2e/test_conversation_ai_extended.py platform/tests/e2e/test_wati_inbound.py platform/tests/e2e/test_auto_enrollment.py -q`

Expected: FAIL on missing `entry_choice_*`, missing questionnaire rephrase/escalation intents, and missing `script_state` on the welcome message row.

- [ ] **Step 6: Commit the failing tests**

```bash
git add platform/tests/e2e/test_conversation_ai_extended.py platform/tests/e2e/test_wati_inbound.py platform/tests/e2e/test_auto_enrollment.py
git commit -m "test: add entry questionnaire regressions"
```

---

### Task 2: Persist questionnaire state on the welcome message

**Files:**
- Modify: `platform/services/integrations/app/main.py`
- Test: `platform/tests/e2e/test_auto_enrollment.py`

- [ ] **Step 1: Update the welcome sender to persist entry state metadata**

Replace the current `variables` setup in `_send_welcome_message()` with:

```python
variables = {
    "1": (contact.first_name or "").strip() or "vous",
    "script_state": {
        "flow": "entry_questionnaire",
        "stage": "awaiting_choice",
        "rephrase_count": 0,
    },
}
```

Leave the provider call unchanged:

```python
result = provider.send_template(contact.phone, "welcome", {"1": variables["1"]})
```

and persist the full `variables` payload on the `Message` row:

```python
row = Message(
    id=f"msg_{uuid4().hex[:8]}",
    contact_id=contact.id,
    template_key="welcome",
    variables=variables,
    provider_message_id=result.get("provider_message_id"),
    status=result.get("status", "queued"),
    provider=result.get("provider", "mock"),
)
```

- [ ] **Step 2: Run the welcome metadata test**

Run: `python -m pytest platform/tests/e2e/test_auto_enrollment.py -k welcome_stores_entry_questionnaire_state -q`

Expected: PASS

- [ ] **Step 3: Commit the welcome-state change**

```bash
git add platform/services/integrations/app/main.py platform/tests/e2e/test_auto_enrollment.py
git commit -m "feat: persist entry questionnaire state on welcome"
```

---

### Task 3: Add deterministic questionnaire and KB routing in conversation AI

**Files:**
- Modify: `platform/services/conversation_ai/app/knowledge_base.py`
- Modify: `platform/services/conversation_ai/app/service.py`
- Test: `platform/tests/e2e/test_conversation_ai_extended.py`

- [ ] **Step 1: Add KB rules for questionnaire choices and free-text buckets**

Insert rules near the top of `KB_GUARDRAIL_RULES`:

```python
{
    "intent": "entry_choice_beginner",
    "reply": "Merci pour ton retour. Le challenge est justement prevu pour repartir sur des bases claires et t'aider a avancer pas a pas.",
    "needs_human": False,
    "exact_messages": {"1"},
},
{
    "intent": "entry_choice_started",
    "reply": "Merci pour ton retour. Le challenge va justement t'aider a remettre les points essentiels dans le bon ordre pour avancer plus proprement.",
    "needs_human": False,
    "exact_messages": {"2"},
},
{
    "intent": "entry_choice_question",
    "reply": "Bien recu. Pose-moi ta question sur le challenge et je te reponds directement.",
    "needs_human": False,
    "exact_messages": {"3"},
},
{
    "intent": "entry_choice_beginner",
    "reply": "Merci pour ton retour. Le challenge est justement prevu pour repartir sur des bases claires et t'aider a avancer pas a pas.",
    "needs_human": False,
    "keywords": [
        "aucune experience",
        "aucune experience en vente en ligne",
        "je pars de zero",
        "je part de zero",
        "de zero",
        "de zer0",
        "debutant",
        "je commence",
        "je n ai pas encore commence",
    ],
    "threshold": 0.88,
},
{
    "intent": "entry_choice_started",
    "reply": "Merci pour ton retour. Le challenge va justement t'aider a remettre les points essentiels dans le bon ordre pour avancer plus proprement.",
    "needs_human": False,
    "keywords": [
        "j ai deja commence",
        "je vends deja",
        "je faisais la vente en ligne",
        "j ai une boutique",
        "je suis deja lance",
        "je vendais deja",
    ],
    "threshold": 0.88,
},
{
    "intent": "entry_choice_question",
    "reply": "Bien recu. Pose-moi ta question sur le challenge et je te reponds directement.",
    "needs_human": False,
    "keywords": [
        "comment ca marche",
        "c est quoi le challenge",
        "horaire",
        "lien",
        "comment participer",
        "comment se passe le challenge",
    ],
    "threshold": 0.88,
},
```

- [ ] **Step 2: Add a helper that marks questionnaire intents as stateful**

In `service.py`, add:

```python
_ENTRY_QUESTIONNAIRE_INTENTS = {
    "entry_choice_beginner",
    "entry_choice_started",
    "entry_choice_question",
}


def _entry_choice_script_state(intent: str) -> dict | None:
    if intent not in _ENTRY_QUESTIONNAIRE_INTENTS:
        return None
    return {
        "flow": "entry_questionnaire",
        "stage": "choice_captured",
        "selected_intent": intent,
        "rephrase_count": 0,
    }
```

- [ ] **Step 3: Attach `script_state` to questionnaire choices in `_knowledge_base_reply()`**

Extend the payload builder:

```python
payload = {
    "reply": rule["reply"],
    "needs_human": rule["needs_human"],
    "intent": rule["intent"],
}
entry_state = _entry_choice_script_state(rule["intent"])
if entry_state:
    payload["script_state"] = entry_state
if "script_state" in rule:
    payload["script_state"] = rule["script_state"]
```

- [ ] **Step 4: Run the direct AI tests**

Run: `python -m pytest platform/tests/e2e/test_conversation_ai_extended.py -q`

Expected: PASS, including `1`, `2`, `3`, `Aucune experience en vente en ligne`, and `Je faisais la vente en ligne...`.

- [ ] **Step 5: Commit the AI routing changes**

```bash
git add platform/services/conversation_ai/app/knowledge_base.py platform/services/conversation_ai/app/service.py platform/tests/e2e/test_conversation_ai_extended.py
git commit -m "feat: add questionnaire entry routing to conversation ai"
```

---

### Task 4: Replace the old scripted follow-up logic with questionnaire-aware inbound handling

**Files:**
- Modify: `platform/services/integrations/app/main.py`
- Test: `platform/tests/e2e/test_wati_inbound.py`

- [ ] **Step 1: Add helpers for questionnaire reformulation and escalation**

Add near the current scripted helpers:

```python
def _entry_questionnaire_rephrase() -> dict:
    return {
        "reply": "Reponds juste avec 1, 2 ou 3 pour que je te reponde correctement.",
        "needs_human": False,
        "intent": "entry_questionnaire_rephrase",
        "script_state": {
            "flow": "entry_questionnaire",
            "stage": "rephrased_once",
            "rephrase_count": 1,
        },
    }


def _entry_questionnaire_escalation() -> dict:
    return {
        "reply": "Je transmets ta demande a l'equipe, quelqu'un te revient dans la journee.",
        "needs_human": True,
        "intent": "human_escalation",
        "send_reply": False,
    }
```

- [ ] **Step 2: Add a questionnaire-state handler**

Implement:

```python
def _entry_questionnaire_reply(latest_outbound: Message, incoming_text: str, result: dict) -> dict | None:
    variables = latest_outbound.variables or {}
    script_state = variables.get("script_state")
    if not isinstance(script_state, dict):
        return None
    if script_state.get("flow") != "entry_questionnaire":
        return None
    if script_state.get("stage") == "choice_captured":
        return result

    if result.get("intent") in {"entry_choice_beginner", "entry_choice_started", "entry_choice_question"}:
        return result

    if script_state.get("rephrase_count", 0) == 0:
        return _entry_questionnaire_rephrase()

    return _entry_questionnaire_escalation()
```

- [ ] **Step 3: Use the questionnaire handler before the old follow-up capture logic**

Inside `_contextual_default_reply()`:

```python
    questionnaire = _entry_questionnaire_reply(latest_outbound, incoming_text, result)
    if questionnaire:
        return questionnaire

    scripted = _scripted_conversation_reply(latest_outbound, incoming_text, result)
    if scripted:
        return scripted
```

And prevent the old follow-up path from hijacking the questionnaire:

```python
if script_state.get("flow") == "entry_questionnaire":
    return None
```

at the top of `_scripted_conversation_reply()`.

- [ ] **Step 4: Ensure rephrase replies persist the updated `script_state`**

No structural change is needed in `_send_ai_session_reply()`, but verify it continues to store:

```python
variables = {"text": reply_text}
if script_state:
    variables["script_state"] = script_state
```

- [ ] **Step 5: Run inbound tests**

Run: `python -m pytest platform/tests/e2e/test_wati_inbound.py -q`

Expected: PASS, especially:

- `Enchante Alban` -> `entry_questionnaire_rephrase` with `queued`
- second off-track reply -> `human_escalation` with `awaiting_human`
- `Aucune experience en vente en ligne` -> `entry_choice_beginner`
- `Je faisais la vente en ligne...` -> `entry_choice_started`

- [ ] **Step 6: Commit the integration-side state machine**

```bash
git add platform/services/integrations/app/main.py platform/tests/e2e/test_wati_inbound.py
git commit -m "feat: add entry questionnaire inbound state machine"
```

---

### Task 5: Update the welcome text and long-term maintenance docs

**Files:**
- Modify: `platform/docs/wati-final/TEMPLATES-WATI-FINAL.md`
- Modify: `platform/docs/wati-final/templates_wati_final.json`
- Modify: `platform/docs/bot-guardrails-system.md`

- [ ] **Step 1: Update the human-readable welcome template text**

Replace the current welcome copy in `platform/docs/wati-final/TEMPLATES-WATI-FINAL.md` with:

```md
Bonjour {{1}},

Ravi de t'avoir avec moi pour le Challenge Amazon FBA.

Pour que je t'oriente correctement, reponds juste avec un chiffre :
1 = je pars de zero
2 = j'ai deja commence a vendre en ligne
3 = j'ai surtout une question sur le challenge
```

- [ ] **Step 2: Update the JSON template reference**

Replace the welcome body in `platform/docs/wati-final/templates_wati_final.json` with:

```json
"body": "Bonjour {{1}},\n\nRavi de t'avoir avec moi pour le Challenge Amazon FBA.\n\nPour que je t'oriente correctement, reponds juste avec un chiffre :\n1 = je pars de zero\n2 = j'ai deja commence a vendre en ligne\n3 = j'ai surtout une question sur le challenge"
```

- [ ] **Step 3: Update the bot guardrails system doc**

Add a section documenting:

```md
## Entry questionnaire

The first-turn bot flow is not open-text anymore.

- `1` -> `entry_choice_beginner`
- `2` -> `entry_choice_started`
- `3` -> `entry_choice_question`

If the lead replies in free text, the KB attempts to map that text to one of the three buckets.
If mapping fails, the bot reformulates once with `Reponds juste avec 1, 2 ou 3...`.
If the next reply still stays off-track, the conversation escalates to human.
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest platform/tests -q`

Expected: PASS

- [ ] **Step 5: Commit the documentation updates**

```bash
git add platform/docs/wati-final/TEMPLATES-WATI-FINAL.md platform/docs/wati-final/templates_wati_final.json platform/docs/bot-guardrails-system.md
git commit -m "docs: update welcome questionnaire and bot guardrails"
```

---

### Task 6: Final verification and production handoff checklist

**Files:**
- Modify: `docs/superpowers/plans/2026-05-26-bot-entry-questionnaire-and-project-kb.md`

- [ ] **Step 1: Run focused conversation checks locally**

Run:

```bash
python -m pytest platform/tests/e2e/test_conversation_ai_extended.py -q
python -m pytest platform/tests/e2e/test_wati_inbound.py -q
```

Expected:

- all questionnaire tests green
- no repeated `Tu peux preciser ?` in entry-flow regressions

- [ ] **Step 2: Run full regression suite**

Run: `python -m pytest platform/tests -q`

Expected: PASS

- [ ] **Step 3: Prepare production verification notes**

Record the exact post-deploy checks:

```text
1. Trigger a fresh registration and confirm the welcome now asks for 1 / 2 / 3.
2. Reply `1` and confirm a short beginner acknowledgment is sent.
3. Reply free text `Aucune experience en vente en ligne` from a fresh lead and confirm it maps to beginner without `Tu peux preciser ?`.
4. Reply `Enchante Alban` from a fresh lead and confirm the bot sends exactly one `Reponds juste avec 1, 2 ou 3...`.
5. Reply another off-track message and confirm the bot stops auto-replying and flags human escalation.
```

- [ ] **Step 4: Commit any final plan adjustments if needed**

```bash
git add docs/superpowers/plans/2026-05-26-bot-entry-questionnaire-and-project-kb.md
git commit -m "docs: finalize entry questionnaire rollout plan"
```

---

## Self-review

### Spec coverage

- entry questionnaire `1 / 2 / 3`: covered in Tasks 1, 3, 5
- free-text interpretation: covered in Tasks 1, 3, 4
- one reformulation then escalation: covered in Tasks 1 and 4
- project KB before OpenAI: covered in Task 3
- welcome metadata and state memory: covered in Task 2
- maintenance and future sessions: covered in Task 5

No spec sections are currently uncovered.

### Placeholder scan

- no `TODO` / `TBD`
- each task has explicit files, commands, expected outcomes, and code snippets

### Type consistency

The plan uses these exact new/updated intents consistently:

- `entry_choice_beginner`
- `entry_choice_started`
- `entry_choice_question`
- `entry_questionnaire_rephrase`
- `human_escalation`

The questionnaire state shape is consistent across tasks:

```json
{
  "flow": "entry_questionnaire",
  "stage": "awaiting_choice|choice_captured|rephrased_once",
  "rephrase_count": 0|1
}
```

