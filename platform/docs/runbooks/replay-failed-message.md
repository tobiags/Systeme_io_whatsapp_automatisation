# Runbook — Rejouer un message échoué

## Identifier le message échoué

```bash
GET /audit/events
```

Filtrer par `name = "message.failed"` et noter l'`aggregate_id`.

## Rejouer manuellement

```bash
POST /messages/send
{
  "contact_id": "<aggregate_id>",
  "template_key": "<template_key>",
  "variables": { "first_name": "<prenom>" }
}
```

## Vérification

Vérifier dans les logs que le statut passe à `queued` puis `delivered`.
