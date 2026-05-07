# n8n — Intégrations et orchestration

n8n est utilisé **uniquement** pour les intégrations externes.
Il ne porte **aucune logique métier critique** — toute décision d'état passe par les services FastAPI.

## Principe

```
Systeme.io ──webhook──▶ n8n ──HTTP POST──▶ /webhooks/systemeio (FastAPI)
StreamYard  ──webhook──▶ n8n ──HTTP POST──▶ /webhooks/streamyard/session
Wati        ──webhook──▶ ──────────────────▶ /webhooks/wati (direct, sans n8n)
```

## Workflows à créer dans n8n

### 1. `systemeio_lead_capture`

**Trigger** : Webhook (POST)
**Action** : HTTP Request → `POST http://api:8000/webhooks/systemeio`
**Body** : transmettre le payload brut Systeme.io tel quel

Payload Systeme.io attendu :
```json
{
  "email": "ada@example.com",
  "phone_number": "+22900000000",
  "first_name": "Ada"
}
```

### 2. `streamyard_session_update`

**Trigger** : Webhook (POST)
**Action** : HTTP Request → `POST http://api:8000/webhooks/streamyard/session`
**Body** :
```json
{
  "challenge_key": "challenge-amazon-fba",
  "edition_key": "2026-05-07-eu",
  "region": "EU",
  "join_url": "https://streamyard.com/XXXX"
}
```

## Règles

- n8n **ne stocke pas** de données métier
- n8n **ne prend pas** de décision de routage ou de segmentation
- En cas d'erreur HTTP depuis FastAPI, n8n peut retry (max 3 fois, backoff 5s)
- Toutes les erreurs sont visibles dans les logs Coolify du service `api`

## Connexion réseau

n8n tourne sur le même VPS, sur le réseau Docker `coolify`.
L'API est accessible via `http://api:8000` depuis n8n.
