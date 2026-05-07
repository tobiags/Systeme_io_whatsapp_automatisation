# Runbook — Rejouer un message échoué

## Contexte

Les messages sont persistés en table `messages` avec un champ `status`.
Statuts possibles : `queued`, `sent`, `failed`.

---

## 1. Identifier les messages échoués

Via l'API (nécessite un endpoint futur) ou directement en base :

```sql
SELECT id, contact_id, template_key, status, created_at
FROM messages
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 50;
```

---

## 2. Rejouer manuellement via l'API

```bash
# Renvoyer un message à un contact
curl -X POST http://whatsapp.178.104.229.163.nip.io/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "ct_XXXXXXXX",
    "template_key": "welcome_j7",
    "variables": {"first_name": "Ada"}
  }'
```

---

## 3. Broadcast de rattrapage pour un cohort

Si un envoi de campagne entier a échoué, relancer via :

```bash
curl -X POST http://whatsapp.178.104.229.163.nip.io/campaigns/broadcast \
  -H "Content-Type: application/json" \
  -d '{"campaign_key": "challenge-amazon-fba", "cohort": "EU"}'
```

---

## 4. Tracer dans l'audit log

Après toute intervention manuelle, consigner l'action :

```bash
curl -X POST http://whatsapp.178.104.229.163.nip.io/audit/events \
  -H "Content-Type: application/json" \
  -d '{
    "name": "message.replayed",
    "aggregate_id": "ct_XXXXXXXX",
    "payload": {"template_key": "welcome_j7", "reason": "provider_timeout", "operator": "tobiags"}
  }'
```

---

## 5. Vérifier les relances humaines en attente

```bash
curl http://whatsapp.178.104.229.163.nip.io/webhooks/wati/queue
```

Ou ouvrir la console admin : `http://admin.178.104.229.163.nip.io`

---

## 6. Prévention

- Les providers (Wati / mock) loguent leurs erreurs dans `messages.status`
- Le provider Wati retourne `{"status": "failed"}` si l'API renvoie une erreur HTTP
- En cas de panne provider, basculer en `WATI_API_URL=` (vide) pour repasser en mock
  sans redéploiement (via Coolify → Secrets → redeploy)
