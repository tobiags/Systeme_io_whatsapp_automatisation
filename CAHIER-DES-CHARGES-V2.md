# Cahier des Charges V2 — Plateforme WhatsApp Challenge Amazon FBA

> Document de référence pour nouvelle session Claude.  
> Remplace le HANDOVER.md initial.  
> Dernière mise à jour : Mai 2026 — commit `16ed68c` sur `master`  
> ⚠️ Lire entièrement avant de toucher au code.

---

## 0. MODE SCAFFOLDING — Règles absolues pour nouvelle session

Avant toute action :

1. Lire ce document en entier
2. Lire `platform/services/campaigns/app/rules.py` (journey + compute_start_step)
3. Lire `platform/services/integrations/app/main.py` (tous les webhooks)
4. Lire `platform/shared/db/models.py` (modèles DB)
5. Lire `platform/services/campaigns/app/main.py` (broadcast + enrollment)
6. Ne jamais réinventer ce qui existe déjà
7. Toujours lancer `python -m pytest tests/ -q` avant et après chaque modification
8. 135 tests doivent passer — si un test casse, le corriger avant de continuer

---

## 1. Contexte projet

Plateforme d'engagement WhatsApp pour un **Challenge Amazon FBA** (3 sessions live, 2×/mois).

- Les inscrits reçoivent des messages WhatsApp automatisés individuels (1-to-1) du J-7 à J+2
- Les inscrits arrivent **chaque jour pendant 7 jours** — c'est le comportement NORMAL, pas une exception
- Chaque inscrit reçoit la séquence adaptée à son jour d'inscription (smart skip automatique)
- Stack : FastAPI monorepo + Celery + PostgreSQL + Redis, déployé sur Coolify VPS

---

## 2. URLs & Accès

| Ressource | URL |
|-----------|-----|
| VPS / plateforme | `http://whatsapp.178.104.229.163.nip.io` |
| Dashboard admin | `http://whatsapp.178.104.229.163.nip.io:3001` |
| Wati tenant | `https://live-mt-server.wati.io/1116186` |
| Webhook Systeme.io | `http://whatsapp.178.104.229.163.nip.io/webhooks/systemeio` |
| Webhook Wati (inbound) | `http://whatsapp.178.104.229.163.nip.io/webhooks/wati` |
| Webhook StreamYard (session) | `POST /webhooks/streamyard/session` |
| Webhook StreamYard (attendance) | `POST /webhooks/streamyard/attendance` |
| Webhook StreamYard (registrants) | `POST /webhooks/streamyard/registrants` |
| Formulaire OnceHub closers | `https://www.ecommercecentrale.com/formulaire-challenge` |

### Variables d'environnement (Coolify)
- `WATI_API_URL` = `https://live-mt-server.wati.io/1116186`
- `WATI_API_TOKEN` = (token Bearer Wati)
- `PLATFORM_API_KEY` = (clé API dashboard admin)
- `OPENAI_API_KEY` = ⚠️ à vérifier dans Coolify
- `CLOSER_NOTIFICATION_EMAIL` = ⚠️ à ajouter — email de notification aux closers

---

## 3. Architecture — services du monorepo

```
platform/
├── services/
│   ├── integrations/       # Webhooks Systeme.io + Wati + StreamYard
│   ├── campaigns/          # Enrôlement, broadcast, Celery tasks
│   ├── conversation_ai/    # Agent IA (règles keyword + GPT-4o-mini)
│   ├── scoring/            # Événements d'engagement + score total
│   ├── contacts/           # CRUD contacts
│   ├── consent/            # Gestion opt-in
│   ├── messaging/          # WatiProvider + MockProvider
│   ├── dashboard_api/      # KPIs + file humaine
│   ├── segmentation/       # Segments froid/tiède/chaud/très_chaud
│   └── improvement_lab/    # Évaluation de candidats
├── apps/
│   └── admin-console/      # React + Tailwind — dashboard opérateur
├── shared/
│   ├── db/models.py        # Tous les modèles SQLAlchemy
│   └── config/settings.py  # Variables d'env (pydantic-settings)
└── tests/                  # 135 tests — tous passent (commit 16ed68c)
```

---

## 4. Cohortes

| Cohorte | Fuseau | Heure live | Région Wati |
|---------|--------|-----------|-------------|
| EU | Europe/Paris | 21h00 | EU |
| US-CA | America/Montreal | 19h00 | US-CA |

Chaque cohorte a ses propres liens StreamYard (3 par cohorte × 2 cohortes = **6 liens par édition**).

---

## 5. Parcours contact COMPLET (état v2 — commit 16ed68c)

### 5.1 Architecture du journey

```python
# campaigns/app/rules.py — DEFAULT_JOURNEY (12 steps, 18 templates)

WELCOME        → template: welcome
COUNTDOWN_J6   → template: countdown_j6
COUNTDOWN_J5   → template: countdown_j5
COUNTDOWN_J4   → template: countdown_j4
COUNTDOWN_J3   → template: countdown_j3
COUNTDOWN_J2   → template: countdown_j2
COUNTDOWN_J1   → template: countdown_j1
DAY_1          → template: live_day1
DAY_2          → 3-way branch (voir §5.3)
DAY_3          → 3-way branch (voir §5.3)
AFTER_1        → 3-way branch (voir §5.3)
AFTER_2        → template: post_followup
```

### 5.2 Smart enrollment — logique de skip automatique

`compute_start_step(days_until_challenge)` dans `campaigns/app/rules.py` :

```
days >= 7  → WELCOME  (séquence complète)
days == 6  → COUNTDOWN_J6  (WELCOME envoyé via webhook, skip au J6)
days == 5  → COUNTDOWN_J5
days == 4  → COUNTDOWN_J4
days == 3  → COUNTDOWN_J3
days == 2  → COUNTDOWN_J2
days == 1  → COUNTDOWN_J1
days == 0  → DAY_1  (challenge aujourd'hui)
days < 0   → DAY_1  (challenge déjà commencé)
```

⚠️ **IMPORTANT** : Les inscrits ne sont pas "tardifs". Les gens s'inscrivent chaque jour pendant les 7 jours avant le challenge — c'est le comportement NORMAL. Le skip automatique est la règle, pas l'exception.

### 5.3 Branching à 3 voies (DAY_2, DAY_3, AFTER_1)

Pour chaque étape avec branching, le système vérifie dans cet ordre :

```
1. ScoreEvent day{N}_live_joined existe ?
   → OUI : template principal (ex: live_day2_attended)
   → NON : continuer ↓

2. ScoreEvent day{N}_streamyard_registered existe ?
   → OUI : template registered_absent (ex: live_day2_registered_absent)
   → NON : template no_show (ex: live_day2_not_registered)
```

Mapping complet :

| Step | Attended | Registered Absent | No Show |
|------|----------|------------------|---------|
| DAY_2 | `live_day2_attended` | `live_day2_registered_absent` | `live_day2_not_registered` |
| DAY_3 | `live_day3_attended` | `live_day3_registered_absent` | `live_day3_not_registered` |
| AFTER_1 | `post_recap_attended` | `post_recap_registered_absent` | `post_recap_not_registered` |

### 5.4 Les 18 templates WhatsApp (à soumettre à Wati)

| # | Clé Wati | Phase | Déclencheur |
|---|----------|-------|-------------|
| 1 | `welcome` | Pre-challenge | Inscription Systeme.io (immédiat) |
| 2 | `countdown_j6` | Pre-challenge | J-6 avant challenge |
| 3 | `countdown_j5` | Pre-challenge | J-5 avant challenge |
| 4 | `countdown_j4` | Pre-challenge | J-4 avant challenge |
| 5 | `countdown_j3` | Pre-challenge | J-3 avant challenge |
| 6 | `countdown_j2` | Pre-challenge | J-2 avant challenge |
| 7 | `countdown_j1` | Pre-challenge | J-1 avant challenge (inclut lien inscription J1) |
| 8 | `live_day1` | Jour 1 | Matin du Jour 1 |
| 9 | `live_day2_attended` | Jour 2 | Lendemain J1 — a assisté J1 |
| 10 | `live_day2_registered_absent` | Jour 2 | Lendemain J1 — inscrit StreamYard J1, absent |
| 11 | `live_day2_not_registered` | Jour 2 | Lendemain J1 — pas inscrit du tout |
| 12 | `live_day3_attended` | Jour 3 | Lendemain J2 — a assisté J2 |
| 13 | `live_day3_registered_absent` | Jour 3 | Lendemain J2 — inscrit StreamYard J2, absent |
| 14 | `live_day3_not_registered` | Jour 3 | Lendemain J2 — pas inscrit du tout |
| 15 | `post_recap_attended` | Post-challenge | 24h après J3 — a assisté J3 |
| 16 | `post_recap_registered_absent` | Post-challenge | 24h après J3 — inscrit StreamYard J3, absent |
| 17 | `post_recap_not_registered` | Post-challenge | 24h après J3 — pas inscrit du tout |
| 18 | `post_followup` | Post-challenge | 48h après J3 — tous |

**+ 1 template hors séquence (⚠️ À IMPLÉMENTER)** :
- `live_day3_offer` — envoyé H+2 après début du Jour 3, aux inscrits StreamYard J3 uniquement

**Catégorie Wati** : `MARKETING` | **Langue** : `fr`

---

## 6. Variables des templates

| Variable | Valeur | Templates concernés |
|----------|--------|-------------------|
| `{{1}}` | Prénom du contact | Tous |
| `{{2}}` | URL inscription StreamYard du jour | `live_day1`, `live_day2_*`, `live_day3_*` |
| `{{2}}` | Heure de la session | `countdown_j1` uniquement |
| `{{3}}` | Heure de la session | `live_day*` |
| `{{form_url}}` | URL formulaire OnceHub closers | `post_recap_*`, `post_followup` (⚠️ À IMPLÉMENTER) |
| `{{payment_url}}` | Lien de paiement programme | `live_day3_offer` (⚠️ À IMPLÉMENTER — URL à obtenir du client) |

⚠️ **IMPORTANT** : Chaque jour du challenge a une URL StreamYard différente.  
Le modèle `ChallengeEdition` doit stocker `day1_url`, `day2_url`, `day3_url` séparément.  
Ce champ n'existe pas encore — **voir §9.1**.

---

## 7. Endpoints disponibles (implémentés)

### Webhooks entrants
```
POST /webhooks/systemeio              # Inscription → upsert contact + consent
POST /webhooks/wati                   # Message inbound → agent IA
POST /webhooks/engagement             # Signaux comportementaux externes (groupe, clic, sondage)
POST /webhooks/streamyard/session     # Enregistrer une édition + URLs
POST /webhooks/streamyard/registrants # Liste inscrits StreamYard → ScoreEvent
POST /webhooks/streamyard/attendance  # Liste présents live → ScoreEvent
GET  /webhooks/streamyard/editions    # Lister toutes les éditions
GET  /webhooks/wati/queue             # File humaine (messages needs_human)
```

### Campagnes
```
POST /campaigns/enroll    # Enrôler un contact dans le journey
POST /campaigns/broadcast # Envoyer messages à tous les contacts au bon step
```

### Scores
```
POST /scores/events       # Créer un événement de score
GET  /scores/{contact_id} # Score total d'un contact
```

### Contacts
```
POST /contacts            # Créer/upsert un contact
GET  /contacts/{id}       # Récupérer un contact
```

---

## 8. Scoring — événements et points

```python
# scoring/app/rules.py — SCORE_RULES

"registered": 10
"group_whatsapp_joined": 15
"opened_message": 5
"clicked_link": 10
"streamyard_link_clicked": 10
"replied_message": 10
"poll_answered": 10
"day1_streamyard_registered": 5    # inscrit sur StreamYard J1
"day2_streamyard_registered": 5    # inscrit sur StreamYard J2
"day3_streamyard_registered": 5    # inscrit sur StreamYard J3
"day1_live_joined": 30             # présent au live J1
"day2_live_joined": 25             # présent au live J2
"day3_live_joined": 25             # présent au live J3
"asked_question": 20
"offer_interest_detected": 20
"conversion_intent_detected": 35
"paid_offer": 50
```

Segments : ≤15 froid | ≤40 tiède | ≤75 chaud | >75 très_chaud

---

## 9. Ce qui reste à implémenter (⚠️ PRIORITAIRE)

### 9.1 Per-day URLs dans ChallengeEdition (BLOQUANT)

**Problème** : `ChallengeEdition.streamyard_url` est un champ unique. Chaque jour a une URL différente.

**Solution** : Ajouter `day1_url`, `day2_url`, `day3_url` au modèle.

Fichiers à modifier :
- `shared/db/models.py` — ajouter 3 colonnes nullable à `ChallengeEdition`
- `integrations/app/main.py` — `streamyard_session` accepte `day_number` optionnel
- `campaigns/app/main.py` — `_build_variables` extrait le numéro du jour depuis `template_key` et utilise le bon URL

```python
# Logique dans _build_variables :
if template_key == "live_day1":
    url = edition.day1_url or edition.streamyard_url
elif template_key.startswith("live_day2"):
    url = edition.day2_url or edition.streamyard_url
elif template_key.startswith("live_day3") or template_key == "live_day3_offer":
    url = edition.day3_url or edition.streamyard_url
```

Commandes curl après implémentation (édition EU — 14-16 mai 2026) :
```bash
# Enregistrer l'édition EU avec les 3 liens
curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{"edition_key":"2026-05-14-eu","region":"EU","challenge_key":"challenge-amazon-fba",
       "day_number":1,"join_url":"https://streamyard.com/watch/MFQraSyVkQFw"}'

curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{"edition_key":"2026-05-14-eu","region":"EU","challenge_key":"challenge-amazon-fba",
       "day_number":2,"join_url":"https://streamyard.com/watch/HkdJRtkdWwff"}'

curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{"edition_key":"2026-05-14-eu","region":"EU","challenge_key":"challenge-amazon-fba",
       "day_number":3,"join_url":"https://streamyard.com/watch/JRQEMxN5TVmX"}'

# Édition US-CA
curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{"edition_key":"2026-05-14-usca","region":"US-CA","challenge_key":"challenge-amazon-fba",
       "day_number":1,"join_url":"https://streamyard.com/watch/P6hNAnj8fxX4"}'

curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{"edition_key":"2026-05-14-usca","region":"US-CA","challenge_key":"challenge-amazon-fba",
       "day_number":2,"join_url":"https://streamyard.com/watch/M57kFyqKJvQE"}'

curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{"edition_key":"2026-05-14-usca","region":"US-CA","challenge_key":"challenge-amazon-fba",
       "day_number":3,"join_url":"https://streamyard.com/watch/BA83sGQvQF9E"}'
```

### 9.2 Auto-enrollment sur inscription Systeme.io (PRIORITAIRE)

**Problème** : Le webhook Systeme.io crée le contact mais ne l'enrôle PAS dans la campagne. L'enrollment est une étape séparée.

**Solution** : Le webhook Systeme.io doit automatiquement :
1. Upsert le contact + consent (déjà fait)
2. Trouver l'édition active pour la cohorte du contact
3. Calculer `days_until_challenge = (edition_date - today).days`
4. Appeler `compute_start_step(days_until_challenge)` 
5. Créer le `CampaignEnrollment` au bon step

Fichier à modifier : `integrations/app/main.py` — dans `systemeio_webhook()`

**Question ouverte** : Comment déterminer la cohorte (EU vs US-CA) depuis le webhook Systeme.io ? Systeme.io a deux listes séparées — le payload doit contenir un indicateur de cohorte, ou on déduit par le numéro de téléphone.

### 9.3 Message H+2 Jour 3 — lien de paiement (NOUVEAU)

**Contexte** : La session Jour 3 dure ~3h. À la 2e heure, le client partage le lien de son programme payant. Ce message doit être envoyé uniquement aux contacts ayant `day3_streamyard_registered`.

**⚠️ URL de paiement manquante** : Le client n'a pas encore fourni le lien de paiement. À demander avant d'implémenter.

**Architecture** :
- Nouveau template Wati : `live_day3_offer` avec `{{1}}` prénom + `{{2}}` lien paiement
- Nouvelle tâche Celery : `dispatch_h_plus_2` (déclenché manuellement par l'opérateur depuis dashboard, 2h après le début du live J3)
- Filtre : uniquement contacts avec ScoreEvent `day3_streamyard_registered`
- Nouveau endpoint dashboard : `POST /dashboard/trigger/day3-offer` pour déclencher manuellement

**Pourquoi manuel** : StreamYard n'a pas d'API publique. On ne peut pas savoir en temps réel qui regarde. Le proxy le plus fiable = `day3_streamyard_registered`.

### 9.4 Notification email aux closers (NOUVEAU)

**Contexte** : Quand un prospect montre un signal d'achat fort, les closers doivent être notifiés par email.

**Déclencheurs** : intent `conversion_intent_detected` ou `offer_interest_detected` ou `needs_human=True` avec priorité `haute`.

**Architecture** :
- Variable d'env `CLOSER_NOTIFICATION_EMAIL` (liste d'emails séparés par virgule)
- Dans `integrations/app/main.py` — après `build_reply()`, si signal fort → envoyer email
- Provider email simple : `httpx` POST vers un SMTP relay ou Mailgun/Resend (à choisir)
- Template email : prénom contact + téléphone + message reçu + score actuel

**⚠️ Provider email à choisir** : Le client ne l'a pas précisé. Demander ou proposer Resend (simple, gratuit jusqu'à 3000 emails/mois).

### 9.5 Formulaire OnceHub dans les messages post-challenge (NOUVEAU)

**URL** : `https://www.ecommercecentrale.com/formulaire-challenge`

**Action** : Injecter cette URL dans les templates `post_recap_attended`, `post_recap_registered_absent`, `post_recap_not_registered`, `post_followup`.

**Architecture** :
- Ajouter variable `{{form_url}}` dans les templates concernés
- Stocker l'URL dans `settings.py` comme `ONCEHUB_FORM_URL` ou en dur dans `_build_variables` (URL stable, ne change pas par édition)

### 9.6 Refonte du doc Word des messages (EN COURS)

Le document v2 est généré (`platform/docs/messages-challenge-amazon-fba-v2.docx`).

**Corrections demandées par le client** :
- J-6 et J-7 : angles différents (J-7 trop similaire à J-6 visuellement)
- Chaque message doit inciter à s'inscrire à la session StreamYard du jour (pas juste regarder)
- Messages `registered_absent` : poser la question "Qu'est-ce qui t'a empêché ?" (conversationnel)
- Messages post-challenge : inclure lien formulaire OnceHub pour réserver un call

**⚠️ Corrections textuelles encore en attente** : Le client a dit "je vais apporter des corrections sur certaines questions". Attendre ses retours avant de finaliser le doc.

---

## 10. Opérations manuelles (rôle du client)

Ces opérations ne peuvent pas être automatisées — StreamYard n'a pas d'API publique.

| Quand | Opération | Durée | Qui |
|-------|-----------|-------|-----|
| Avant chaque édition | Enregistrer les 6 liens StreamYard (3 EU + 3 US-CA) via curl ou dashboard | ~5 min | Client ou assistant |
| Après chaque live J1 | Exporter participants StreamYard → POST /webhooks/streamyard/attendance | ~5 min | Client ou assistant |
| Après chaque live J2 | Idem | ~5 min | Client ou assistant |
| Après chaque live J3 | Idem | ~5 min | Client ou assistant |
| Pendant live J3 à H+2 | Déclencher manuellement le message de paiement depuis dashboard | ~1 min | Client ou assistant |

**Le groupe WhatsApp** reste géré manuellement par le client. L'API WhatsApp Business ne permet pas de poster dans un groupe — c'est une limitation technique de Meta, pas de la plateforme.

---

## 11. Limites techniques confirmées (ne pas promettre ce qui est impossible)

| Limitation | Raison | Alternative |
|------------|--------|-------------|
| Broadcast dans groupe WhatsApp | WhatsApp Business API = 1-to-1 uniquement | Manuel par client |
| Automatisation StreamYard | Pas d'API publique StreamYard | Curl manuel 5 min |
| Temps réel présents pendant live | Pas d'API temps réel | Proxy = `streamyard_registered` |
| Multi-utilisateurs dashboard | Non implémenté | Un seul rôle admin pour l'instant |

---

## 12. Décisions prises (ne pas revenir dessus sans raison)

| Décision | Contexte |
|----------|----------|
| 18 templates (pas 10) | Branching 3 voies + 7 countdowns demandé par client |
| Clés templates en anglais snake_case | Convention cohérente avec le codebase |
| Closers notifiés par email | Client a confirmé — pas via dashboard |
| OnceHub = `ecommercecentrale.com/formulaire-challenge` | URL fournie par client |
| `day3_streamyard_registered` comme proxy présents H+2 | Faute d'API temps réel StreamYard |
| Opérations StreamYard manuelles | Pas d'API publique — confiré après recherche |
| Message H+2 J3 déclenché manuellement | Pas d'API temps réel StreamYard |
| URL paiement J3 inconnue | À demander au client (non fournie à ce jour) |

---

## 13. Questions ouvertes (à résoudre avant d'implémenter)

1. **URL de paiement programme** : quel est le lien exact pour rejoindre/payer le programme ? (pour le template `live_day3_offer`)
2. **Provider email closers** : quel service utiliser pour les notifications ? (Resend, Mailgun, SMTP ?)
3. **Adresse email closers** : quelle adresse recevoir les notifications ?
4. **Cohorte depuis Systeme.io** : comment distinguer EU vs US-CA dans le payload webhook ? Y a-t-il un champ dans Systeme.io qui indique la liste d'origine ?
5. **Corrections du doc Word** : le client doit envoyer ses corrections sur les templates avant soumission à Wati

---

## 14. Architecture du code — fichiers clés

| Fichier | Rôle |
|---------|------|
| `campaigns/app/rules.py` | Journey (12 steps) + compute_start_step |
| `campaigns/app/main.py` | Endpoint enroll + broadcast 3-way |
| `campaigns/app/tasks.py` | Celery tasks H-6/H-45/H-10 |
| `integrations/app/main.py` | Tous les webhooks entrants |
| `integrations/app/normalizer.py` | Normalisation payload Systeme.io |
| `conversation_ai/app/service.py` | Agent IA + GPT-4o-mini |
| `conversation_ai/app/prompts.py` | FAQ + règles keyword |
| `scoring/app/rules.py` | Barème points |
| `shared/db/models.py` | Modèles SQLAlchemy |
| `shared/config/settings.py` | Variables d'env |
| `docs/messages-challenge-amazon-fba-v2.docx` | Doc Word client (18 templates) |
| `docs/generate-templates-doc-v2.js` | Script générateur du doc Word |

---

## 15. État des tests

- **135 tests** passent au commit `16ed68c`
- Nouveaux fichiers de tests : `test_streamyard_registrants.py`, `test_smart_enrollment_skip.py`
- Commande : `cd platform && python -m pytest tests/ -q`

---

## 16. Git — historique récent

```
16ed68c  feat(v2): 3-way branching, 7 countdowns, smart skip, StreamYard registrants
d5604e9  docs: add HANDOVER.md
45fb246  fix(campaigns): inject real variables + call WatiProvider
dfb0399  feat(dashboard): full redesign Tailwind + Phosphor icons + API key auth
```

---

## 17. Prochaines implémentations — ordre suggéré

1. ✅ `shared/db/models.py` → `day1_url`, `day2_url`, `day3_url` sur `ChallengeEdition` (commit 28d9737)
2. ✅ `integrations/app/main.py` → `streamyard_session` accepte `day_number` (commit 28d9737)
3. ✅ `campaigns/app/main.py` → `_build_variables` utilise URL par jour + OnceHub + payment URL (commit 28d9737)
4. ✅ `integrations/app/main.py` → auto-enrollment dans `systemeio_webhook` (commit 28d9737)
5. ✅ Notification email closers → `services/notifications/app/email.py` (commit 28d9737)
6. ✅ Message H+2 Jour 3 → `dispatch_h_plus_2` Celery + `POST /campaigns/trigger/day3-offer` (commit 28d9737)
7. ✅ Variables OnceHub dans templates post-challenge (`post_*` → `settings.oncehub_form_url`) (commit 28d9737)
8. ✅ Webhook comportemental générique `/webhooks/engagement` + scoring `replied_message` / `poll_answered`
9. ✅ Lecture Wati `opened_message` corrigée pour appliquer les 5 points prévus
10. ⏳ Corriger doc Word v2 avec retours client (en attente des 18 templates corrigés du client)
11. ⏳ `program_payment_url` — en attente du lien de paiement fourni par le client

**Variables d'environnement à configurer en prod (Coolify) :**
```
CLOSER_NOTIFICATION_EMAIL=closer1@team.com,closer2@team.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=expediteur@ecommercecentrale.com
SMTP_PASSWORD=...
SMTP_FROM=noreply@ecommercecentrale.com
PROGRAM_PAYMENT_URL=https://...  ⚠️ À fournir par le client
ONCEHUB_FORM_URL=https://www.ecommercecentrale.com/formulaire-challenge  (valeur par défaut)
```

**Test suite :** 177 tests passing
