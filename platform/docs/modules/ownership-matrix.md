# Matrice d'ownership des modules

| Module | Service | Responsabilité |
|--------|---------|----------------|
| Platform Core | `api_gateway` | Point d'entrée, health, routing |
| Contacts | `contacts` | Création, mise à jour, cycle de vie |
| Consentement | `consent` | Opt-in, opt-out, éligibilité |
| Campagnes | `campaigns` | Séquences J-7 → Jour 3, cohortes EU/US-CA |
| Messaging | `messaging` | Envoi WhatsApp, abstraction provider |
| Scoring | `scoring` | Calcul score d'engagement |
| Segmentation | `segmentation` | Attribution segment froid/tiède/chaud/très chaud |
| Intégrations | `integrations` | Systeme.io, StreamYard, Stripe |
| Dashboard | `dashboard_api` | KPIs, read models, vues opérateur |
| IA Conv. | `conversation_ai` | FAQ, objections, escalade humaine |
| Observabilité | `observability` | Logs, audit trail, replay |
| Improvement Lab | `improvement_lab` | Évaluations offline, candidats prompts |
