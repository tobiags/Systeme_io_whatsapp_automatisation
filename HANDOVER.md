# Handover — Plateforme WhatsApp Challenge Amazon FBA

> Document de passation pour nouvelle session Claude.  
> Dernière mise à jour : Mai 2026 — commit `45fb246` sur `master`

---

## 1. Contexte projet

Plateforme d'engagement WhatsApp pour un **Challenge Amazon FBA** (3 sessions live, 2×/mois).  
Les inscrits reçoivent une séquence de 10 messages WhatsApp automatisés de J-7 à J+2.  
Stack : FastAPI monorepo + Celery + PostgreSQL + Redis, déployé sur **Coolify VPS**.

---

## 2. URLs & accès

| Ressource | URL / valeur |
|-----------|-------------|
| VPS / plateforme | `http://whatsapp.178.104.229.163.nip.io` |
| Dashboard admin | `http://whatsapp.178.104.229.163.nip.io:3001` |
| Wati tenant | `https://live-mt-server.wati.io/1116186` |
| Webhook Systeme.io | `http://whatsapp.178.104.229.163.nip.io/webhooks/systemeio` |
| Webhook Wati (inbound) | `http://whatsapp.178.104.229.163.nip.io/webhooks/wati` |
| Webhook StreamYard (session) | `POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session` |
| Webhook StreamYard (attendance) | `POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/attendance` |
| Repo GitHub | (repo privé sur compte utilisateur) |

### Variables d'environnement (déjà dans Coolify)
- `WATI_API_URL` = `https://live-mt-server.wati.io/1116186`
- `WATI_API_TOKEN` = (token Bearer Wati)
- `PLATFORM_API_KEY` = (clé API dashboard admin)
- `OPENAI_API_KEY` = ⚠️ **À VÉRIFIER / AJOUTER dans Coolify** si pas encore fait

---

## 3. Architecture — services du monorepo

```
platform/
├── services/
│   ├── integrations/       # Webhooks Systeme.io + Wati + StreamYard
│   ├── campaigns/          # Enrôlement, broadcast, Celery tasks H-6/H-45/H-10
│   ├── conversation_ai/    # Agent IA (règles + GPT-4o-mini fallback)
│   ├── scoring/            # Événements d'engagement + score total
│   ├── contacts/           # CRUD contacts
│   ├── consent/            # Gestion opt-in
│   ├── messaging/          # WatiProvider + MockProvider
│   ├── dashboard_api/      # KPIs + file humaine
│   ├── segmentation/       # Segments froid/tiède/chaud/très_chaud
│   └── improvement_lab/    # Évaluation de candidats (prompts / messages)
├── apps/
│   └── admin-console/      # React + Tailwind — dashboard opérateur
├── shared/
│   ├── db/models.py        # Tous les modèles SQLAlchemy
│   └── config/settings.py  # Variables d'env (pydantic-settings)
└── tests/                  # 113 tests e2e — tous passent
```

---

## 4. Parcours contact (Journey)

| Step | Template envoyé | Déclencheur |
|------|----------------|-------------|
| J-7 | `welcome_j7` | Inscription Systeme.io |
| J-6 | `content_j6` | 24h après welcome_j7 |
| DAY_1 | `challenge_day_1` | Webhook StreamYard session (2h avant live J1) |
| DAY_2 | `challenge_day_2` ou `challenge_day_2_catchup` | Webhook StreamYard J2 + score day1_live_joined |
| DAY_3 | `challenge_day_3` ou `challenge_day_3_catchup` | Webhook StreamYard J3 + score day2_live_joined |
| AFTER_1 | `post_challenge_recap` ou `post_challenge_missed` | 24h après fin J3 + score day3_live_joined |
| AFTER_2 | `post_challenge_followup` | 48h après fin J3 |

### Logique de branchement
- Si `day{N}_live_joined` ScoreEvent existe → template **principal** (engagé)
- Sinon → template **catchup** (absent)
- Les ScoreEvents de présence se créent via `POST /webhooks/streamyard/attendance`

---

## 5. Variables des templates WhatsApp

| Variable | Valeur | Source |
|----------|--------|--------|
| `{{1}}` | Prénom du contact | `Contact.first_name` |
| `{{2}}` | URL StreamYard live | `ChallengeEdition.streamyard_url` |
| `{{3}}` | Heure de session | Cohort config (`21:00` pour EU) |

**Cohorts :**
- EU : `Europe/Paris`, live à `21:00`
- US-CA : `America/Montreal`, live à `19:00`

---

## 6. Les 10 templates WhatsApp — état de validation

> Document client : `platform/docs/messages-challenge-amazon-fba.docx`  
> Script générateur : `platform/docs/generate-templates-doc.js`

| # | Clé Wati | Statut |
|---|----------|--------|
| 1 | `welcome_j7` | ⏳ En attente validation client |
| 2 | `content_j6` | ⏳ En attente validation client |
| 3 | `challenge_day_1` | ⏳ En attente validation client |
| 4 | `challenge_day_2` | ⏳ En attente validation client |
| 5 | `challenge_day_2_catchup` | ⏳ En attente validation client |
| 6 | `challenge_day_3` | ⏳ En attente validation client |
| 7 | `challenge_day_3_catchup` | ⏳ En attente validation client |
| 8 | `post_challenge_recap` | ⏳ En attente validation client |
| 9 | `post_challenge_missed` | ⏳ En attente validation client |
| 10 | `post_challenge_followup` | ⏳ En attente validation client |

**Catégorie Wati :** `MARKETING` | **Langue :** `fr`

---

## 7. Ce qui est ✅ TERMINÉ (code + tests + déployé)

- [x] Monorepo FastAPI 12 services — déployé sur Coolify
- [x] Webhook Systeme.io → upsert contact + consent opt-in
  - Normalizer gère les 2 formats : `contact.fields[]` (réel) et flat (legacy)
- [x] Webhook Wati inbound → agent IA (règles keyword + GPT-4o-mini)
- [x] Webhook Wati read receipt → ScoreEvent `opened_message`
- [x] Webhook StreamYard session → stockage ChallengeEdition + scheduling Celery
- [x] **Webhook StreamYard attendance** → `POST /webhooks/streamyard/attendance`  
  (batch de phones → ScoreEvents `day{N}_live_joined`, idempotent)
- [x] Broadcast campaigns → variables injectées + WatiProvider appelé directement
- [x] Celery tasks H-6/H-45/H-10/recap → WatiProvider réel (plus de mock hardcodé)
- [x] Scoring + segmentation (froid/tiède/chaud/très_chaud)
- [x] Dashboard admin React (Tailwind) — auth gate API key, KPIs, file humaine
- [x] System prompt GPT-4o-mini enrichi (9 leviers marketing psychology)
- [x] 113 tests e2e — tous passent

---

## 8. Ce qui reste ⏳ À FAIRE

### 8.1 Configurations (pas de code)

#### A. Systeme.io
1. Se connecter à Systeme.io → Automations
2. Créer une automation déclenchée à l'inscription au funnel du challenge
3. Action : **Webhook POST** vers `http://whatsapp.178.104.229.163.nip.io/webhooks/systemeio`
4. Payload attendu (format réel Systeme.io) :
```json
{
  "contact": {
    "email": "prenom@email.com",
    "fields": [
      {"slug": "first_name", "value": "Prénom"},
      {"slug": "phone", "value": "+33600000001"}
    ]
  },
  "event": "optin"
}
```

#### B. Coolify — redeploy + OPENAI_API_KEY
1. Coolify → projet → redeploy pour prendre le commit `45fb246`
2. Vérifier que `OPENAI_API_KEY` est bien défini dans les variables d'env
3. Si absent → l'ajouter (GPT-4o-mini ne fonctionnera pas sans)

#### C. Wati — créer les 10 templates
> **Attendre la validation du client sur le doc Word d'abord**
1. Wati dashboard → Template Messages → Add New Template
2. Pour chaque template : copier texte + variables, catégorie MARKETING, langue fr
3. Soumettre → approbation Meta (délai 24-72h)

#### D. StreamYard — webhook session
Pour chaque nouvelle édition du challenge, envoyer manuellement :
```bash
curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/session \
  -H "Content-Type: application/json" \
  -d '{
    "edition_key": "2026-05-07-eu",
    "region": "EU",
    "join_url": "https://streamyard.com/watch/XXXX",
    "challenge_key": "challenge-amazon-fba"
  }'
```

#### E. StreamYard — attendance après chaque live
Après chaque session, envoyer la liste des participants :
```bash
curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/streamyard/attendance \
  -H "Content-Type: application/json" \
  -d '{
    "edition_key": "2026-05-07-eu",
    "day_number": 1,
    "attendees": ["33600000001", "33600000002"]
  }'
```

### 8.2 Optionnel (améliorations futures)

- [ ] Bouton "Répondre" dans le dashboard admin (envoyer un message depuis la file humaine)
- [ ] Automatisation de l'export des participants StreamYard (aujourd'hui manuel)
- [ ] Page de stats par édition dans le dashboard
- [ ] Intégration Zapier/Make pour automatiser l'envoi de l'attendance StreamYard

---

## 9. Fichiers clés à connaître

| Fichier | Rôle |
|---------|------|
| `platform/services/campaigns/app/rules.py` | Définition du journey (10 steps) |
| `platform/services/campaigns/app/main.py` | Endpoint broadcast + injection variables |
| `platform/services/campaigns/app/tasks.py` | Celery tasks H-6/H-45/H-10 |
| `platform/services/integrations/app/main.py` | Tous les webhooks entrants |
| `platform/services/integrations/app/normalizer.py` | Normalisation payload Systeme.io |
| `platform/services/conversation_ai/app/service.py` | Agent IA + system prompt GPT |
| `platform/services/conversation_ai/app/prompts.py` | FAQ + règles keyword |
| `platform/services/scoring/app/rules.py` | Barème points par événement |
| `platform/shared/db/models.py` | Tous les modèles DB |
| `platform/shared/config/settings.py` | Variables d'env |
| `platform/docs/messages-challenge-amazon-fba.docx` | Doc Word client (10 templates) |

---

## 10. Commandes utiles

```bash
# Tests
cd platform && python -m pytest tests/ -q

# Lancer localement
docker-compose up

# Vérifier les logs en prod (via Coolify)
# Coolify → projet → Logs

# Tester le webhook Systeme.io en local
curl -X POST http://localhost:8000/webhooks/systemeio \
  -H "Content-Type: application/json" \
  -d '{"contact": {"email": "test@test.com", "fields": [{"slug": "first_name", "value": "Test"}, {"slug": "phone", "value": "+33600000001"}]}, "event": "optin"}'

# Tester l'agent IA
curl -X POST http://localhost:8000/webhooks/wati \
  -H "Content-Type: application/json" \
  -d '{"waId": "33600000001", "text": "combien ca coute", "eventType": "messageReceived"}'
```

---

## 11. Git — historique récent

```
45fb246  fix(campaigns): inject real variables + call WatiProvider on broadcast and Celery tasks
fa88692  chore(admin): add .gitignore, remove node_modules from tracking
dfb0399  feat(dashboard): full redesign with Tailwind + Phosphor icons + API key auth gate
95bd1b7  feat(campaigns): add AFTER_1 + AFTER_2 post-challenge steps to journey
2038a5a  feat(dashboard): add messages_sent_total KPI + full spec §11.4 test coverage
1c4d6d7  fix(systemeio): normalizer now handles real Systeme.io webhook format
```
