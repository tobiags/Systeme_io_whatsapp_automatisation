# n8n — Intégrations et orchestration

n8n est utilisé uniquement pour les intégrations externes (webhooks Systeme.io, Stripe, StreamYard).

Il ne porte aucune logique métier critique. Toute décision d'état passe par les services FastAPI.

## Workflows actifs

- `systemeio_lead_capture` : reçoit le webhook Systeme.io, appelle POST /webhooks/systemeio
- `streamyard_session` : reçoit le lien de session, appelle POST /webhooks/streamyard/session

## Connexion à la DB

Host : `platform-db`
Port : `5432`
Database : `platform`
