# Runbook de déploiement

## Prérequis

- VPS avec Docker installé
- Repo GitHub connecté à Coolify
- PostgreSQL `platform-db` en cours d'exécution sur le réseau `coolify`

## Procédure

1. Renseigner les variables d'environnement sur Coolify :
   - `POSTGRES_DSN=postgresql+psycopg://platform:PASSWORD@platform-db:5432/platform`
   - `REDIS_URL=redis://redis:6379/0`
   - `WATI_API_URL=...`
   - `WATI_API_TOKEN=...`
   - `OPENAI_API_KEY=...`

2. Connecter le repo GitHub à Coolify (auto-deploy sur push)

3. Exécuter les migrations Alembic :
   ```bash
   alembic upgrade head
   ```

4. Vérifier `/health` sur l'API Gateway

5. Vérifier les webhooks provider (Systeme.io, Wati)

## Rollback

```bash
alembic downgrade -1
```
