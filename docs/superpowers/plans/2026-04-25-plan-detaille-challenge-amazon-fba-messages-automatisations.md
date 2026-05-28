# Plan d'implementation detaille - Messages et automatisations du Challenge Amazon FBA

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** definir et implementer le plan ultra detaille des messages, regles d'automatisation, variantes de cohortes, FAQ, relances et points de reprise humaine pour le `Challenge Amazon FBA`.

**Architecture:** moteur de campagnes pilote par edition et cohorte, templates de messages versionnes, scheduler evenementiel, FAQ bornees, regles de relance comportementales, et suivi des evenements temps reel vers dashboard et scoring.

**Tech Stack:** FastAPI, PostgreSQL, Redis, Celery, n8n pour integrations, Pydantic, pytest, dashboard admin, Prompt Registry pour versions de messages.

---

## Portee de ce plan

Ce plan couvre uniquement :

- les messages a envoyer avant, pendant et apres le challenge
- les automatisations associees
- les variantes `EU` et `US-CA`
- les evenements fonctionnels a suivre
- les FAQ et objections a injecter dans le service conversationnel
- les relances manuelles et escalades

Ce plan ne couvre pas :

- l'infrastructure generale de la plateforme
- la securite transverse
- le detail technique des providers WhatsApp

---

## Hypotheses fonctionnelles

- le programme s'appelle `Challenge Amazon FBA`
- chaque edition dure `3 jours`, du `jeudi au samedi`
- le challenge a lieu `2 fois par mois`
- deux cohortes sont gerees : `EU` et `US-CA`
- les cohortes proviennent de `deux listes Systeme.io distinctes`
- horaire live `EU` : `21h00 Europe`
- horaire live `US-CA` : `19h00 Montreal / New York`
- les liens StreamYard changent a chaque edition
- les liens StreamYard sont prepares a l'avance, envoyes par email, puis republies dans les groupes du challenge
- l'audience est majoritairement debutante
- les objections dominantes sont financieres
- une partie importante des objections apparait pendant le live et doit alimenter les suivis post-live

---

## Structure fonctionnelle cible des messages

Les messages doivent etre classes par :

- `edition`
- `cohorte`
- `moment`
- `segment`
- `statut comportemental`
- `intention conversationnelle`

Les grandes familles de templates sont :

- `welcome`
- `orientation`
- `live_reminder`
- `link_delivery`
- `missed_live_recovery`
- `post_live_recap`
- `faq_answer`
- `financial_objection`
- `installment_plan_followup`
- `trust_reassurance`
- `next_challenge_followup`
- `conversion_followup`
- `human_escalation`

---

### Tache 1: Modeliser les editions, cohortes et fenetres horaires du challenge

**Files:**
- Create: `platform/docs/modules/challenge-editions.md`
- Create: `platform/services/campaigns/app/challenge_editions.py`
- Create: `platform/services/campaigns/app/cohorts.py`
- Create: `platform/tests/contract/test_challenge_editions.py`

- [ ] **Step 1: Ecrire le test de mapping edition/cohorte**

```python
from services.campaigns.app.challenge_editions import build_challenge_session


def test_build_challenge_session_for_eu():
    session = build_challenge_session(
        challenge_key="challenge-amazon-fba",
        edition_key="2026-05-07",
        cohort="EU",
    )
    assert session["challenge_key"] == "challenge-amazon-fba"
    assert session["cohort"] == "EU"
    assert session["live_time"] == "21:00"
    assert session["timezone"] == "Europe/Paris"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_challenge_editions.py -v`
Expected: FAIL because edition builder is missing

- [ ] **Step 3: Ecrire l'implementation minimale**

```python
def build_challenge_session(challenge_key: str, edition_key: str, cohort: str) -> dict:
    if cohort == "EU":
        return {
            "challenge_key": challenge_key,
            "edition_key": edition_key,
            "cohort": "EU",
            "live_time": "21:00",
            "timezone": "Europe/Paris",
        }
    return {
        "challenge_key": challenge_key,
        "edition_key": edition_key,
        "cohort": "US-CA",
        "live_time": "19:00",
        "timezone": "America/Montreal",
    }
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_challenge_editions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-editions.md platform/services/campaigns/app/challenge_editions.py platform/services/campaigns/app/cohorts.py platform/tests/contract/test_challenge_editions.py
git commit -m "feat: add challenge editions and cohort scheduling model"
```

---

### Tache 2: Definir le catalogue de templates de messages

**Files:**
- Create: `platform/docs/modules/challenge-message-catalog.md`
- Create: `platform/shared/contracts/challenge_messages.py`
- Create: `platform/services/campaigns/app/message_catalog.py`
- Create: `platform/tests/contract/test_challenge_message_catalog.py`

- [ ] **Step 1: Ecrire le test du catalogue minimal**

```python
from services.campaigns.app.message_catalog import MESSAGE_CATALOG


def test_message_catalog_contains_critical_templates():
    assert "welcome_registration" in MESSAGE_CATALOG
    assert "day1_live_reminder" in MESSAGE_CATALOG
    assert "day2_reengagement" in MESSAGE_CATALOG
    assert "financial_objection_soft" in MESSAGE_CATALOG
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_challenge_message_catalog.py -v`
Expected: FAIL because message catalog is missing

- [ ] **Step 3: Ecrire le catalogue minimal**

```python
MESSAGE_CATALOG = {
    "welcome_registration": {"family": "welcome", "channels": ["whatsapp"]},
    "cohort_orientation": {"family": "orientation", "channels": ["whatsapp"]},
    "day1_live_reminder": {"family": "live_reminder", "channels": ["whatsapp"]},
    "day2_reengagement": {"family": "missed_live_recovery", "channels": ["whatsapp"]},
    "day3_final_push": {"family": "live_reminder", "channels": ["whatsapp"]},
    "financial_objection_soft": {"family": "financial_objection", "channels": ["whatsapp"]},
}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_challenge_message_catalog.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-message-catalog.md platform/shared/contracts/challenge_messages.py platform/services/campaigns/app/message_catalog.py platform/tests/contract/test_challenge_message_catalog.py
git commit -m "feat: add challenge message catalog"
```

---

### Tache 3: Implementer la sequence post-inscription et pre-challenge

**Files:**
- Create: `platform/docs/modules/challenge-prelaunch-sequence.md`
- Create: `platform/services/campaigns/app/prelaunch_rules.py`
- Create: `platform/services/campaigns/app/prelaunch_scheduler.py`
- Create: `platform/tests/e2e/test_prechallenge_sequence.py`

- [ ] **Step 1: Ecrire le test de sequence post-inscription**

```python
from services.campaigns.app.prelaunch_rules import build_prechallenge_sequence


def test_prechallenge_sequence_contains_orientation_and_reminder():
    sequence = build_prechallenge_sequence(cohort="EU")
    keys = [item["template_key"] for item in sequence]
    assert "welcome_registration" in keys
    assert "cohort_orientation" in keys
    assert "day1_opening_reminder" in keys
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_prechallenge_sequence.py -v`
Expected: FAIL because prechallenge builder is missing

- [ ] **Step 3: Ecrire la sequence minimale**

```python
def build_prechallenge_sequence(cohort: str) -> list[dict]:
    return [
        {"template_key": "welcome_registration", "offset": "immediate", "cohort": cohort},
        {"template_key": "cohort_orientation", "offset": "immediate", "cohort": cohort},
        {"template_key": "email_delivery_expectation", "offset": "immediate", "cohort": cohort},
        {"template_key": "day1_opening_reminder", "offset": "day1_minus_6h", "cohort": cohort},
    ]
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_prechallenge_sequence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-prelaunch-sequence.md platform/services/campaigns/app/prelaunch_rules.py platform/services/campaigns/app/prelaunch_scheduler.py platform/tests/e2e/test_prechallenge_sequence.py
git commit -m "feat: add pre-challenge automation sequence"
```

---

### Tache 4: Definir les messages et automatismes du Jour 1

**Files:**
- Create: `platform/docs/modules/challenge-day1.md`
- Create: `platform/services/campaigns/app/day1_rules.py`
- Create: `platform/tests/e2e/test_day1_automation.py`

- [ ] **Step 1: Ecrire le test des automatismes Jour 1**

```python
from services.campaigns.app.day1_rules import build_day1_sequence


def test_day1_sequence_contains_link_and_recap():
    sequence = build_day1_sequence(cohort="US-CA")
    keys = [item["template_key"] for item in sequence]
    assert "day1_live_reminder" in keys
    assert "day1_streamyard_link" in keys
    assert "day1_post_live_recap" in keys
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_day1_automation.py -v`
Expected: FAIL because day1 rules are missing

- [ ] **Step 3: Ecrire les regles Jour 1**

```python
def build_day1_sequence(cohort: str) -> list[dict]:
    return [
        {"template_key": "day1_live_reminder", "offset": "day1_minus_6h", "cohort": cohort},
        {"template_key": "day1_streamyard_link", "offset": "day1_minus_45m", "cohort": cohort},
        {"template_key": "day1_last_call", "offset": "day1_minus_10m", "cohort": cohort},
        {"template_key": "day1_post_live_recap", "offset": "day1_plus_2h", "cohort": cohort},
        {"template_key": "day1_pitch_objection_followup", "offset": "day1_plus_6h", "cohort": cohort},
    ]
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_day1_automation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-day1.md platform/services/campaigns/app/day1_rules.py platform/tests/e2e/test_day1_automation.py
git commit -m "feat: add day 1 challenge automations"
```

---

### Tache 5: Definir les messages et automatismes du Jour 2

**Files:**
- Create: `platform/docs/modules/challenge-day2.md`
- Create: `platform/services/campaigns/app/day2_rules.py`
- Create: `platform/tests/e2e/test_day2_automation.py`

- [ ] **Step 1: Ecrire le test des automatismes Jour 2**

```python
from services.campaigns.app.day2_rules import build_day2_sequence


def test_day2_sequence_contains_reengagement_path():
    sequence = build_day2_sequence(cohort="EU")
    keys = [item["template_key"] for item in sequence]
    assert "day2_live_reminder" in keys
    assert "day2_reengagement" in keys
    assert "day2_post_live_recap" in keys
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_day2_automation.py -v`
Expected: FAIL because day2 rules are missing

- [ ] **Step 3: Ecrire les regles Jour 2**

```python
def build_day2_sequence(cohort: str) -> list[dict]:
    return [
        {"template_key": "day2_live_reminder", "offset": "day2_minus_6h", "cohort": cohort},
        {"template_key": "day2_streamyard_link", "offset": "day2_minus_45m", "cohort": cohort},
        {"template_key": "day2_reengagement", "offset": "day2_plus_3h_if_missed_day1", "cohort": cohort},
        {"template_key": "day2_post_live_recap", "offset": "day2_plus_2h", "cohort": cohort},
        {"template_key": "day2_payment_plan_followup", "offset": "day2_plus_6h_if_requested", "cohort": cohort},
    ]
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_day2_automation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-day2.md platform/services/campaigns/app/day2_rules.py platform/tests/e2e/test_day2_automation.py
git commit -m "feat: add day 2 challenge automations"
```

---

### Tache 6: Definir les messages et automatismes du Jour 3

**Files:**
- Create: `platform/docs/modules/challenge-day3.md`
- Create: `platform/services/campaigns/app/day3_rules.py`
- Create: `platform/tests/e2e/test_day3_automation.py`

- [ ] **Step 1: Ecrire le test des automatismes Jour 3**

```python
from services.campaigns.app.day3_rules import build_day3_sequence


def test_day3_sequence_contains_final_push_and_offer_followup():
    sequence = build_day3_sequence(cohort="EU")
    keys = [item["template_key"] for item in sequence]
    assert "day3_final_push" in keys
    assert "day3_streamyard_link" in keys
    assert "post_challenge_offer_followup" in keys
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_day3_automation.py -v`
Expected: FAIL because day3 rules are missing

- [ ] **Step 3: Ecrire les regles Jour 3**

```python
def build_day3_sequence(cohort: str) -> list[dict]:
    return [
        {"template_key": "day3_final_push", "offset": "day3_minus_6h", "cohort": cohort},
        {"template_key": "day3_streamyard_link", "offset": "day3_minus_45m", "cohort": cohort},
        {"template_key": "day3_last_call", "offset": "day3_minus_10m", "cohort": cohort},
        {"template_key": "post_challenge_offer_followup", "offset": "day3_plus_3h", "cohort": cohort},
        {"template_key": "next_challenge_followup", "offset": "day3_plus_24h_if_requested", "cohort": cohort},
    ]
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_day3_automation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-day3.md platform/services/campaigns/app/day3_rules.py platform/tests/e2e/test_day3_automation.py
git commit -m "feat: add day 3 challenge automations"
```

---

### Tache 7: Definir les variantes de messages par comportement

**Files:**
- Create: `platform/docs/modules/challenge-behavioral-branches.md`
- Create: `platform/services/campaigns/app/behavioral_rules.py`
- Create: `platform/tests/contract/test_behavioral_branches.py`

- [ ] **Step 1: Ecrire le test de branche comportementale**

```python
from services.campaigns.app.behavioral_rules import classify_branch


def test_classify_branch_for_registered_but_inactive():
    branch = classify_branch({
        "registered": True,
        "clicked_link": False,
        "attended_day1": False,
        "asked_question": False,
    })
    assert branch == "inactive_registered"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_behavioral_branches.py -v`
Expected: FAIL because behavioral classifier is missing

- [ ] **Step 3: Ecrire le classifieur minimal**

```python
def classify_branch(signals: dict) -> str:
    if signals.get("attended_day1") and signals.get("asked_question"):
        return "engaged_attendee"
    if signals.get("registered") and not signals.get("clicked_link"):
        return "inactive_registered"
    if signals.get("clicked_link") and not signals.get("attended_day1"):
        return "clicked_but_absent"
    return "default"
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_behavioral_branches.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-behavioral-branches.md platform/services/campaigns/app/behavioral_rules.py platform/tests/contract/test_behavioral_branches.py
git commit -m "feat: add behavioral branching for challenge messaging"
```

---

### Tache 8: Definir les FAQ et reponses bornees du challenge

**Files:**
- Create: `platform/docs/modules/challenge-faq.md`
- Create: `platform/services/conversation-ai/app/challenge_faq.py`
- Create: `platform/tests/contract/test_challenge_faq.py`

- [ ] **Step 1: Ecrire le test de FAQ critique**

```python
from services.conversation-ai.app.challenge_faq import CHALLENGE_FAQ


def test_challenge_faq_contains_core_questions():
    assert "faq_whatsapp_group_join" in CHALLENGE_FAQ
    assert "faq_email_missing" in CHALLENGE_FAQ
    assert "faq_start_time" in CHALLENGE_FAQ
    assert "faq_offer_price" in CHALLENGE_FAQ
    assert "faq_next_challenge_date" in CHALLENGE_FAQ
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_challenge_faq.py -v`
Expected: FAIL because challenge faq registry is missing

- [ ] **Step 3: Ecrire le registre minimal**

```python
CHALLENGE_FAQ = {
    "faq_whatsapp_group_join": "Le lien du groupe WhatsApp est envoye dans votre sequence de bienvenue.",
    "faq_email_missing": "Verifiez vos spams. Si besoin, un conseiller peut verifier votre inscription.",
    "faq_start_time": "Le challenge commence du jeudi au samedi selon votre cohorte horaire.",
    "faq_offer_price": "Le challenge est gratuit. Les details de l'offre sont presentes pendant le parcours.",
    "faq_next_challenge_date": "Le challenge revient deux fois par mois. La prochaine edition peut vous etre communiquee directement.",
}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_challenge_faq.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-faq.md platform/services/conversation-ai/app/challenge_faq.py platform/tests/contract/test_challenge_faq.py
git commit -m "feat: add challenge faq registry"
```

---

### Tache 9: Definir les objections financieres et reponses associees

**Files:**
- Create: `platform/docs/modules/challenge-financial-objections.md`
- Create: `platform/services/conversation-ai/app/financial_objections.py`
- Create: `platform/tests/contract/test_financial_objections.py`

- [ ] **Step 1: Ecrire le test d'objection financiere**

```python
from services.conversation-ai.app.financial_objections import detect_financial_objection


def test_detect_financial_objection():
    result = detect_financial_objection("Je n'ai pas le budget pour investir maintenant")
    assert result["detected"] is True
    assert result["strength"] in {"soft", "strong"}
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_financial_objections.py -v`
Expected: FAIL because objection detector is missing

- [ ] **Step 3: Ecrire le detecteur minimal**

```python
def detect_financial_objection(text: str) -> dict:
    normalized = text.lower()
    keywords = ["budget", "cher", "prix", "investir", "cout", "coûte", "coute"]
    detected = any(keyword in normalized for keyword in keywords)
    strength = "strong" if "pas le budget" in normalized or "trop cher" in normalized else "soft"
    return {"detected": detected, "strength": strength if detected else None}
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_financial_objections.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-financial-objections.md platform/services/conversation-ai/app/financial_objections.py platform/tests/contract/test_financial_objections.py
git commit -m "feat: add financial objection detection for challenge"
```

---

### Tache 10: Definir les evenements fonctionnels a suivre dans le challenge

**Files:**
- Create: `platform/docs/modules/challenge-events.md`
- Create: `platform/shared/contracts/challenge_events.py`
- Create: `platform/tests/contract/test_challenge_events.py`

- [ ] **Step 1: Ecrire le test des evenements critiques**

```python
from shared.contracts.challenge_events import CHALLENGE_EVENT_NAMES


def test_challenge_events_include_live_and_conversation_tracking():
    assert "lead_captured" in CHALLENGE_EVENT_NAMES
    assert "day1_live_joined" in CHALLENGE_EVENT_NAMES
    assert "financial_objection_detected" in CHALLENGE_EVENT_NAMES
    assert "followup_manual_queued" in CHALLENGE_EVENT_NAMES
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/contract/test_challenge_events.py -v`
Expected: FAIL because event registry is missing

- [ ] **Step 3: Ecrire le registre minimal**

```python
CHALLENGE_EVENT_NAMES = [
    "lead_captured",
    "challenge_edition_assigned",
    "cohort_assigned",
    "streamyard_link_sent",
    "streamyard_link_clicked",
    "day1_live_joined",
    "day2_live_joined",
    "day3_live_joined",
    "faq_detected",
    "financial_objection_detected",
    "human_escalation_required",
    "followup_manual_queued",
]
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/contract/test_challenge_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-events.md platform/shared/contracts/challenge_events.py platform/tests/contract/test_challenge_events.py
git commit -m "feat: add challenge event registry"
```

---

### Tache 11: Definir les regles de segmentation specifiques au challenge

**Files:**
- Create: `platform/docs/modules/challenge-segmentation.md`
- Create: `platform/services/segmentation/app/challenge_segmentation.py`
- Create: `platform/tests/e2e/test_challenge_segmentation.py`

- [ ] **Step 1: Ecrire le test de segmentation challenge**

```python
from services.segmentation.app.challenge_segmentation import classify_challenge_segment


def test_classify_challenge_segment_for_attendee_with_offer_interest():
    segment = classify_challenge_segment({
        "attended_day1": True,
        "attended_day2": True,
        "attended_day3": False,
        "clicked_offer": True,
        "financial_objection": True,
    })
    assert segment == "tres_chaud"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_challenge_segmentation.py -v`
Expected: FAIL because challenge segmentation rules are missing

- [ ] **Step 3: Ecrire les regles minimales**

```python
def classify_challenge_segment(signals: dict) -> str:
    attendance = sum(1 for key in ["attended_day1", "attended_day2", "attended_day3"] if signals.get(key))
    if attendance >= 2 and signals.get("clicked_offer"):
        return "tres_chaud"
    if attendance >= 1:
        return "chaud"
    if signals.get("registered"):
        return "tiede"
    return "froid"
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_challenge_segmentation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-segmentation.md platform/services/segmentation/app/challenge_segmentation.py platform/tests/e2e/test_challenge_segmentation.py
git commit -m "feat: add challenge-specific segmentation rules"
```

---

### Tache 12: Definir la priorisation operateur et les escalades humaines

**Files:**
- Create: `platform/docs/modules/challenge-operator-priority.md`
- Create: `platform/services/conversation-ai/app/operator_priority.py`
- Create: `platform/tests/e2e/test_operator_priority.py`

- [ ] **Step 1: Ecrire le test de priorite operateur**

```python
from services.conversation-ai.app.operator_priority import compute_operator_priority


def test_operator_priority_for_engaged_financial_objection_is_high():
    priority = compute_operator_priority({
        "attended_day1": True,
        "attended_day2": True,
        "pricing_question": True,
        "financial_objection": True,
    })
    assert priority == "high"
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_operator_priority.py -v`
Expected: FAIL because operator prioritizer is missing

- [ ] **Step 3: Ecrire la logique minimale**

```python
def compute_operator_priority(signals: dict) -> str:
    if signals.get("financial_objection") and (signals.get("attended_day1") or signals.get("attended_day2")):
        return "high"
    if signals.get("pricing_question"):
        return "medium"
    return "low"
```

- [ ] **Step 4: Relancer le test**

Run: `pytest platform/tests/e2e/test_operator_priority.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-operator-priority.md platform/services/conversation-ai/app/operator_priority.py platform/tests/e2e/test_operator_priority.py
git commit -m "feat: add operator prioritization for challenge followups"
```

---

### Tache 13: Definir le flux E2E complet du challenge

**Files:**
- Create: `platform/docs/modules/challenge-e2e-flow.md`
- Create: `platform/tests/e2e/test_challenge_message_flow.py`

- [ ] **Step 1: Ecrire le test de flux fonctionnel complet**

```python
from services.campaigns.app.prelaunch_rules import build_prechallenge_sequence
from services.campaigns.app.day1_rules import build_day1_sequence
from services.campaigns.app.day2_rules import build_day2_sequence
from services.campaigns.app.day3_rules import build_day3_sequence


def test_full_challenge_message_flow_has_all_major_phases():
    pre = build_prechallenge_sequence("EU")
    day1 = build_day1_sequence("EU")
    day2 = build_day2_sequence("EU")
    day3 = build_day3_sequence("EU")

    all_keys = [item["template_key"] for item in pre + day1 + day2 + day3]
    assert "welcome_registration" in all_keys
    assert "day1_streamyard_link" in all_keys
    assert "day2_reengagement" in all_keys
    assert "post_challenge_offer_followup" in all_keys
```

- [ ] **Step 2: Lancer le test et verifier qu'il echoue**

Run: `pytest platform/tests/e2e/test_challenge_message_flow.py -v`
Expected: FAIL until all previous challenge modules are implemented

- [ ] **Step 3: Rendre les references coherentes entre modules**

```python
CHALLENGE_TEMPLATE_KEYS = [
    "welcome_registration",
    "cohort_orientation",
    "day1_opening_reminder",
    "day1_live_reminder",
    "day1_streamyard_link",
    "day1_post_live_recap",
    "day2_live_reminder",
    "day2_reengagement",
    "day2_post_live_recap",
    "day3_final_push",
    "day3_streamyard_link",
    "post_challenge_offer_followup",
]
```

- [ ] **Step 4: Lancer la suite challenge**

Run: `pytest platform/tests/contract/test_challenge_* platform/tests/e2e/test_*challenge* -v`
Expected: PASS on all challenge-specific contract and e2e tests

- [ ] **Step 5: Commit**

```bash
git add platform/docs/modules/challenge-e2e-flow.md platform/tests/e2e/test_challenge_message_flow.py
git commit -m "feat: validate end-to-end challenge messaging flow"
```

---

## Ordre recommande de production des contenus

1. templates de bienvenue et orientation
2. messages Jour 1
3. messages Jour 2
4. messages Jour 3
5. FAQ debutants
6. messages objections financieres
7. messages post-challenge conversion
8. scripts d'escalade humaine

## Mapping recommande par LLM

1. `LLM-3` : editions, cohortes, sequences, scheduler, branches comportementales
2. `LLM-6` : FAQ, objections, escalades, ton conversationnel
3. `LLM-5` : segmentation challenge et signaux de scoring
4. `LLM-7` : liens StreamYard et evenements externes associes
5. `LLM-8` : visualisation dashboard des performances challenge

## Definition of done du challenge

- chaque edition du challenge peut etre instanciee avec une cohorte `EU` ou `US-CA`
- tous les templates critiques sont catalogues
- les sequences pre-challenge, Jour 1, Jour 2, Jour 3 existent
- les variantes comportementales sont definies
- les FAQ debutants sont bornees
- les objections financieres sont detectees
- les evenements critiques sont traces
- les regles de segmentation challenge sont explicites
- la priorisation operateur est definie
- le flux E2E du challenge est verifie

---

## Ajustements suite au retour client

Ces points doivent etre consideres comme prioritaires pour la suite du plan :

- les cohortes `EU` et `US-CA` existent deja dans `deux listes Systeme.io distinctes`
- les liens `StreamYard` sont prepares a l'avance, envoyes par `email`, puis repostes dans les `groupes` pendant les jours du challenge
- les objections apparaissent surtout `en direct pendant le live`, donc le systeme doit surtout organiser le `suivi post-live`

### Messages supplementaires a prevoir

- `email_delivery_expectation`
- `day1_pitch_objection_followup`
- `day2_payment_plan_followup`
- `payment_failed_followup`
- `skeptic_reassurance_followup`
- `next_challenge_followup`

### FAQ supplementaires a ajouter

- `faq_next_challenge_date`

### Sous-categories d'objections financieres a distinguer

- `budget`
- `installment_plan`
- `payment_failure`
- `delay`
- `skepticism`

### Evenements supplementaires a tracer

- `email_live_link_sent`
- `group_live_link_posted`
- `installment_plan_requested`
- `payment_failed_insufficient_funds`
- `skepticism_detected`
- `next_challenge_requested`

### Regles de priorisation operateur a renforcer

- priorite `high` pour tentative de paiement sans fonds suffisants
- priorite `high` pour demande explicite de plan de paiement
- priorite `medium` pour scepticisme apres participation au live
- priorite `medium` pour demande sur la prochaine date du challenge si le lead est engage
