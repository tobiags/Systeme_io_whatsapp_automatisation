# Runbook — Déploiement sur VPS (Coolify)

## Pré-requis

- VPS Ubuntu avec Docker et Coolify v3.12.36 installés
- Repo GitHub public : `tobiags/Systeme_io_whatsapp_automatisation`
- Base de données PostgreSQL `platform-db` démarrée sur le réseau Docker `coolify`
- URL cible API : `http://whatsapp.178.104.229.163.nip.io`
- Redis requis pour Celery (`worker` / `beat`) - fourni par le stack Docker Compose de la plateforme

---

## 1. Premier déploiement

### 1.1 Ajouter l'application dans Coolify

1. Ouvrir Coolify → **New Resource** → **Public Repository from Git**
2. URL du repo : `https://github.com/tobiags/Systeme_io_whatsapp_automatisation`
3. Build pack : **Docker Compose**
4. Fichier Docker Compose : `/docker-compose.prod.yml`
5. Domaine : `whatsapp.178.104.229.163.nip.io`

### 1.2 Ajouter les secrets (Coolify → Secrets)

| Variable | Valeur |
|---|---|
| `POSTGRES_DSN` | `postgresql+psycopg://platform:changeme@platform-db:5432/platform` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `WATI_API_URL` | URL de l'API Wati (ex : `https://live-server-XYZ.wati.io`) |
| `WATI_API_TOKEN` | Token Bearer Wati |
| `OPENAI_API_KEY` | Clé API OpenAI (optionnel) |

### 1.3 Lancer le déploiement

Cliquer **Deploy** dans Coolify. Le processus :
1. Clone le repo
2. Build l'image Docker (`platform/Dockerfile`)
3. Lance `alembic upgrade head` (toutes les migrations)
4. Démarre les services du stack :
   - `redis`
   - `api`
   - `admin`
   - `worker`
   - `beat`

### 1.4 Vérifier le déploiement

```bash
curl http://whatsapp.178.104.229.163.nip.io/health
# {"status":"ok","db":true}

curl http://whatsapp.178.104.229.163.nip.io/services
# {"services": [...]}
```

---

## 2. Mise à jour (redéploiement)

1. Pousser les changements sur `master` : `git push origin master`
2. Dans Coolify → **Force Redeploy**

> Les nouvelles migrations Alembic sont appliquées automatiquement au démarrage.
>
> Si les messages quotidiens ou les rappels live ne partent pas, vérifier d'abord que `redis`, `worker` et `beat` sont bien lancés dans le stack principal.

---

## 3. Admin Console (frontend React)

Dans Coolify, créer un **second service** :
1. **New Resource** → **Public Repository from Git** → même repo
2. Build pack : **Docker Compose** → service `admin`
3. Domaine : `admin.178.104.229.163.nip.io`
4. Build arg : `VITE_API_URL=http://whatsapp.178.104.229.163.nip.io`

---

## 4. Webhook Wati (messages entrants)

Dans le dashboard Wati → **Settings → Webhook** :
- URL : `http://whatsapp.178.104.229.163.nip.io/webhooks/wati`
- Events : **Message Received**

Test :
```bash
curl -X POST http://whatsapp.178.104.229.163.nip.io/webhooks/wati \
  -H "Content-Type: application/json" \
  -d '{"waId":"+33612345678","text":{"body":"Bonjour !"}}'
```

---

## 5. Webhook Systeme.io

Dans Systeme.io → **Funnel → Automation → Webhook** :
- URL : `http://whatsapp.178.104.229.163.nip.io/webhooks/systemeio`
- Méthode : POST, déclencher sur : **Form submitted** / **Opt-in**

---

## 6. Rollback

Si un déploiement casse la prod :
1. Dans Coolify → historique des déploiements → **Redeploy** sur le build stable
2. OU `git revert HEAD && git push` pour un rollback propre via CI
