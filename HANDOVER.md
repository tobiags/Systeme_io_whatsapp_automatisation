# HANDOVER — Plateforme WhatsApp Challenge Amazon FBA
> Mis à jour : 2026-05-29 · À utiliser au démarrage de la prochaine session

---

## 1. Vue d'ensemble du projet

Système d'engagement WhatsApp automatisé pour un Challenge Amazon FBA de 3 jours.  
**500+ contacts** reçoivent des messages WhatsApp en séquence : pre-challenge → Day 1 → Day 2 → Day 3 → post-challenge.

**Deux cohortes parallèles :**
- `EU` — Europe (timezone Paris, live à 21h00)
- `US-CA` — Amérique du Nord (timezone Montréal, live à 19h00)

**Repo GitHub :** `https://github.com/tobiags/Systeme_io_whatsapp_automatisation`  
**Branche principale :** `master`

---

## 2. Infrastructure de production

| Composant | Valeur |
|-----------|--------|
| Plateforme API | `http://whatsapp.178.104.229.163.nip.io` |
| API Key | `0467f002e78953afe434e2b73df8abdc5168efbef3c05e3178bf0b6281eda447` |
| Serveur | VPS `root@whatsapp-fba` (accès via Termius) |
| DB | Docker `platform-db` → PostgreSQL, DB `platform`, user `platform` |
| Hébergement | Coolify sur le VPS |

**Accès DB direct (Termius) :**
```bash
docker exec -it platform-db psql -U platform -d platform
```

---

## 3. Édition active

| Paramètre | Valeur |
|-----------|--------|
| `edition_key` | `2026-05-28-usca` |
| `cohort` | `US-CA` |
| `edition_date` | `2026-05-28` (= Day 1) |
| Day 1 | 2026-05-28 ✅ terminé |
| Day 2 | 2026-05-29 ⚠️  terminé avec problème US/CA (voir §4) |
| Day 3 | 2026-05-30 🔴 demain |

---

## 4. Problème US/CA MARKETING — État au 2026-05-29

### Cause racine
Meta bloque les templates **MARKETING** pour les numéros +1 (US/Canada).  
321 contacts sur 483 ont reçu `status: "failed"` au broadcast Day 2.

### Résultat du broadcast Day 2
```
Total envoyés : 483
US/CA (+1)    : 321 → FAILED (Meta bloque MARKETING)
Non-US        : 162 → queued (livraison OK)
```

### Fix code déployé (commit `9ce3ac5`)
Le code détecte automatiquement les numéros +1 et route vers `template_key + "_utility"` :
- `platform/services/campaigns/app/main.py` → `broadcast_campaign_impl` + `trigger_day3_offer`
- `platform/services/campaigns/app/tasks.py` → `_dispatch_messages_for_cohort`

Fonction de détection :
```python
def _is_us_ca_phone(phone: str) -> bool:
    p = phone.strip().lstrip("+")
    if p.startswith("00"): p = p[2:]
    return len(p) == 11 and p.startswith("1")
```

### Templates UTILITY créés dans Wati — en attente approbation Meta
| Template | Catégorie | Statut |
|----------|-----------|--------|
| `live_day2_not_registered_utility` | UTILITY | ⏳ Pending |
| `live_day2_attended_v2_utility` | UTILITY | ⏳ Pending |
| `live_day2_registered_absent_utility` | UTILITY | ⏳ Pending |
| `live_day3_not_registered_utility` | UTILITY | ⏳ Pending |
| `live_day3_attended_v2_utility` | UTILITY | ⏳ Pending |
| `live_day3_registered_absent_utility` | UTILITY | ⏳ Pending |
| `live_day3_offer_hplus2_utility` | UTILITY | ⏳ Pending |

### Templates UTILITY MANQUANTS — à créer dans Wati maintenant
| À créer | Copier le contenu de |
|---------|---------------------|
| `live_day3_h10_utility` | `live_day3_h10` |
| `live_day3_hplus5_utility` | `live_day3_hplus5` |

### Procédure de récupération Day 2 (dès approbation Meta)
```bash
# 1. Déployer le code
cd /opt/platform && git pull origin master && docker compose restart platform

# 2. Reset du verrou broadcast Day 2
curl -X POST http://whatsapp.178.104.229.163.nip.io/admin/reset-broadcast-lock \
  -H "X-API-Key: 0467f002e78953afe434e2b73df8abdc5168efbef3c05e3178bf0b6281eda447" \
  -H "Content-Type: application/json" \
  -d '{"edition_key": "2026-05-28-usca", "local_date": "2026-05-29"}'

# 3. Re-broadcast — seulement les 321 US/CA encore à DAY_2 reçoivent
curl -X POST http://whatsapp.178.104.229.163.nip.io/campaigns/broadcast \
  -H "X-API-Key: 0467f002e78953afe434e2b73df8abdc5168efbef3c05e3178bf0b6281eda447" \
  -H "Content-Type: application/json" \
  -d '{"campaign_key": "challenge-amazon-fba", "cohort": "US-CA", "edition_key": "2026-05-28-usca"}'
```

### Plan B — si Day 3 arrive avant l'approbation
```bash
# Avancer les 321 contacts bloqués à DAY_2 → DAY_3
# D'abord dry_run pour confirmer le nombre
curl -X POST http://whatsapp.178.104.229.163.nip.io/admin/advance-step \
  -H "X-API-Key: 0467f002e78953afe434e2b73df8abdc5168efbef3c05e3178bf0b6281eda447" \
  -H "Content-Type: application/json" \
  -d '{"edition_key": "2026-05-28-usca", "from_step": "DAY_2", "to_step": "DAY_3", "dry_run": true}'

# Si count correct (~321) → lancer le vrai
  -d '{"edition_key": "2026-05-28-usca", "from_step": "DAY_2", "to_step": "DAY_3", "dry_run": false}'
```

---

## 5. Architecture de la plateforme

```
Systeme_io_whatsapp_automatisation/
├── platform/                    ← Plateforme principale
│   ├── services/
│   │   ├── campaigns/app/
│   │   │   ├── main.py          ← POST /campaigns/broadcast (MODIFIÉ)
│   │   │   ├── tasks.py         ← Celery H-2/H-10/H+5 (MODIFIÉ)
│   │   │   ├── rules.py         ← DEFAULT_JOURNEY (12 étapes)
│   │   │   └── scheduler.py     ← Scheduling Celery tasks
│   │   ├── dashboard_api/app/
│   │   │   └── admin.py         ← /admin/* (MODIFIÉ: +advance-step)
│   │   ├── integrations/app/    ← Webhooks Systeme.io, Wati, StreamYard
│   │   ├── messaging/app/       ← Wati provider
│   │   ├── conversation_ai/app/ ← Bot IA LEGACY (à remplacer)
│   │   └── api_gateway/app/     ← Entrée unique, auth middleware
│   ├── shared/db/models.py      ← 11 tables SQLAlchemy
│   └── alembic/                 ← Migrations DB
└── bot/                         ← NOUVEAU bot indépendant (voir §6)
    ├── app/
    │   ├── main.py              ← FastAPI, POST /webhook/wati
    │   ├── engine.py            ← Claude API + historique 10 turns
    │   ├── guardrails.py        ← Escalade critique
    │   └── wati_client.py       ← sendSessionMessage
    └── Dockerfile               ← Image standalone pour Coolify
```

### Endpoints clés de la plateforme
| Endpoint | Méthode | Usage |
|----------|---------|-------|
| `/campaigns/broadcast` | POST | Broadcast journalier |
| `/campaigns/trigger/day3-offer` | POST | Offre H+2 Day 3 |
| `/admin/diagnostics` | GET | État DB complet + enrollments_by_step |
| `/admin/advance-step` | POST | Débloquer contacts stuck à une étape |
| `/admin/reset-broadcast-lock` | POST | Annuler verrou journalier |
| `/admin/re-enroll` | POST | Réinscrire contacts manquants |
| `/webhooks/systemeio` | POST | Nouveau lead depuis Systeme.io |
| `/webhooks/wati` | POST | Messages entrants (bot LEGACY) |
| `/health` | GET | Health check |

---

## 6. Nouveau bot indépendant (`bot/`)

### Pourquoi recréer le bot
Le bot actuel (`services/conversation_ai`) est :
- Couplé au gateway principal (si le gateway tombe, le bot tombe)
- Sans mémoire de conversation (contexte vide à chaque message)
- Basé sur des règles regex rigides
- Difficile à déployer indépendamment

### Ce que fait le nouveau bot
| Fonctionnalité | Détail |
|----------------|--------|
| Webhook | `POST /webhook/wati` (port 8001) |
| Mémoire | 10 derniers messages de la DB → contexte Claude |
| IA | Claude Haiku (Anthropic) |
| Guardrails | Détection paiement/plainte/juridique → escalade humaine |
| Scoring | Écrit dans `score_events` (replied_message +10, asked_question +20) |
| Admin | `GET /admin/stats`, `POST /admin/auto-reply/toggle` |
| DB | Lit/écrit dans le même Postgres que la plateforme |

### Variables d'environnement pour Coolify
```env
POSTGRES_DSN=postgresql://platform:platform@<ip-db>:5432/platform
WATI_API_URL=https://live-mt-server.wati.io/1116186
WATI_API_TOKEN=<bearer_token_wati>
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
BOT_API_KEY=<secret_admin>
AUTO_REPLY_ENABLED=true
MAX_HISTORY_MESSAGES=10
DEDUP_WINDOW_SECONDS=60
CLOSER_EMAIL=closer@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
```

### Déploiement sur Coolify
1. Coolify → **New Service → Docker** → pointer sur le dossier `bot/`
2. Build context : `bot/`, Dockerfile : `bot/Dockerfile`
3. Configurer les variables d'environnement ci-dessus
4. Exposer le port `8001`
5. Créer un domaine : ex. `bot.whatsapp.178.104.229.163.nip.io`
6. **Changer le webhook dans Wati dashboard :**
   - Ancien : `http://whatsapp.178.104.229.163.nip.io/webhooks/wati`
   - Nouveau : `http://bot.whatsapp.178.104.229.163.nip.io/webhook/wati`
7. Désactiver auto-reply sur le service legacy : `WHATSAPP_AUTO_REPLY_ENABLED=false`
8. Tester avec un vrai message → vérifier `GET /admin/stats`

---

## 7. Journey Map

```
WELCOME → COUNTDOWN_J6 → J5 → J4 → J3 → J2 → J1
→ DAY_1  (live_day1)
→ DAY_2  (3-way: live_day2_attended_v2 / registered_absent / not_registered)
         (+_utility pour +1 US/CA)
→ DAY_3  (3-way: live_day3_attended_v2 / registered_absent / not_registered)
         (+_utility pour +1 US/CA)
→ AFTER_1 (3-way: post_recap_attended / registered_absent / not_registered)
→ AFTER_2 (post_testimonials)
→ AFTER_3 (post_inaction_reason)
→ AFTER_4 (post_closer_call)
→ completed
```

**Règle step progression :**
- Si Wati retourne `status: queued` → contact avance à l'étape suivante
- Si Wati retourne `status: failed` → contact reste à l'étape actuelle

---

## 8. Schéma DB

```
contacts             → leads (phone UNIQUE, first_name)
consents             → opted_in status (proof_source: systemeio_registration)
campaign_enrollments → contact + current_step + edition_key + cohort
challenge_editions   → edition_key, edition_date, day1/2/3_url, payment_url
messages             → outbound audit (template_key, status, variables JSON)
inbound_messages     → bot audit (text, ai_reply, intent, needs_human)
score_events         → log immuable d'engagement (event_type, points)
contact_scores       → score total courant (upsert)
segments             → froid/tiède/chaud/très_chaud
audit_events         → idempotency locks (broadcast journalier)
```

---

## 9. Commits importants

| Commit | Description |
|--------|-------------|
| `60016a4` | fix(infra): remplace curl health check par urllib |
| `df132f2` | fix(wati): strip 00-prefix phones + persist Wati errors |
| `06bb900` | fix(broadcasting): 3 bugs causing <10% delivery |
| `698b293` | feat(admin): advance-step endpoint + enrollments_by_step diagnostics |
| `9ce3ac5` | fix(campaigns): routing US/CA +1 → templates _utility |

---

## 10. Prochaines étapes

### Urgent (avant Day 3 = 2026-05-30)
- [ ] Créer `live_day3_h10_utility` dans Wati (UTILITY)
- [ ] Créer `live_day3_hplus5_utility` dans Wati (UTILITY)
- [ ] Attendre approbation Meta des 7 templates UTILITY existants
- [ ] Dès approbation : reset lock + re-broadcast Day 2 pour 321 US/CA
- [ ] git pull sur le serveur + restart platform

### Après le challenge
- [ ] Déployer le nouveau bot (`bot/`) sur Coolify (instance séparée)
- [ ] Changer le webhook Wati vers la nouvelle URL du bot
- [ ] Désactiver le bot legacy (`WHATSAPP_AUTO_REPLY_ENABLED=false`)
- [ ] Créer les templates `_utility` pour toute la prochaine édition

---

## 11. Commandes de diagnostic rapide

```bash
# Health check
curl http://whatsapp.178.104.229.163.nip.io/health

# Diagnostics complets (enrollments_by_step pour voir les contacts bloqués)
curl http://whatsapp.178.104.229.163.nip.io/admin/diagnostics \
  -H "X-API-Key: 0467f002e78953afe434e2b73df8abdc5168efbef3c05e3178bf0b6281eda447" | python3 -m json.tool

# État des enrollments US-CA par étape (DB direct)
docker exec -it platform-db psql -U platform -d platform -c \
"SELECT current_step, count(*) FROM campaign_enrollments
 WHERE edition_key = '2026-05-28-usca' GROUP BY 1 ORDER BY 2 DESC;"

# Messages Day 2 par statut
docker exec -it platform-db psql -U platform -d platform -c \
"SELECT template_key, status, count(*) FROM messages
 WHERE template_key LIKE 'live_day2%' GROUP BY 1, 2 ORDER BY 1, 2;"

# Vérifier si une approbation Meta a changé les statuts Wati
# → Aller dans Wati dashboard → Templates → filtrer par UTILITY
```
