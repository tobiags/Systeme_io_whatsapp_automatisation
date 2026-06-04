# Project Routing

This repository has global `gstack` skills installed under `C:\Users\tobid\.claude\skills\gstack` (garrytan/gstack) and `superpowers` skills under `C:\Users\tobid\.codex\superpowers` (obra/superpowers, v5.1.0).
For this project, use only the subset below unless the user explicitly asks for something else.

## Skill routing

### Use these gstack skills

`/gstack`
- Use for browser-based dogfooding of the admin console and public flows.
- Primary targets:
  - `http://whatsapp.178.104.229.163.nip.io`
  - `http://whatsapp.178.104.229.163.nip.io:3001`
- Good for smoke checks after frontend or integration changes.

`/qa`
- Use after meaningful UI, dashboard, or workflow changes.
- Scope for this repo:
  - login/API-key flow on the admin console
  - dashboard refresh/loading states
  - operator queue visibility
  - key challenge flows when a local or deployed UI is available

`/review`
- Use before landing substantial backend or workflow changes.
- Especially useful after touching:
  - `platform/services/campaigns/*`
  - `platform/services/integrations/*`
  - `platform/services/conversation_ai/*`
  - `platform/shared/db/*`

`/scrape`
- Use only for read-only web extraction when Browser/Firecrawl is not the better fit.
- Good candidates:
  - extracting structured details from StreamYard/WawPlus public docs
  - pulling non-authenticated product/help content

## Prefer other tools first when they fit better

- Prefer `context7` for versioned library/framework documentation.
- Prefer `firecrawl-mcp` for external product docs, web research, and cleaner scraping.
- Prefer Browser or Chrome tools for interactive debugging when an in-app or logged-in browser matters.

## Do not use these gstack skills by default in this repo

Avoid unless the user explicitly asks:
- design-focused skills (`gstack-design-*`)
- benchmarking/canary skills
- deployment/ship automation skills
- office-hours, retro, or generic product strategy skills
- gbrain setup/sync skills

## Project-specific notes

- This project is backend/integration-heavy. `gstack` is complementary, not the main workflow.
- Do not rely on gstack for source-of-truth API documentation. Use `context7`, Firecrawl, or official docs.
- For changes that affect the dashboard, run browser QA before claiming completion.
- For Wati/Systeme.io/StreamYard/WawPlus behavior, validate implementation with docs first, then use browser QA only for visible flows.

## Minimal recommended workflow

1. Use `context7` or Firecrawl to verify third-party docs when behavior is uncertain.
2. Implement or adjust code locally.
3. Run repo tests.
4. Use `/qa` or `/gstack` if the change touches a visible operator flow.
5. Use `/review` before final landing when the diff is substantial.
