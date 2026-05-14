# n8n — Integrations and orchestration

n8n is used only for external integrations and operator-side glue.
It does not own business state or routing decisions. FastAPI remains the source of truth.

## Principle

```text
Systeme.io ──webhook──▶ n8n ──HTTP POST──▶ /webhooks/systemeio
StreamYard  ──manual/export──▶ n8n ──HTTP POST──▶ /webhooks/streamyard/*
WawPlus     ──webhook──▶ n8n ──HTTP POST──▶ /webhooks/engagement
Wati        ──webhook──▶ ─────────────────▶ /webhooks/wati (direct)
```

## Workflow inventory

The importable workflow files live in `platform/infra/n8n/workflows/`.

1. `systemeio_lead_capture_eu.json`
2. `systemeio_lead_capture_usca.json`
3. `streamyard_session_update.json`
4. `streamyard_registrants_sync.json`
5. `streamyard_attendance_sync.json`
6. `engagement_signal_ingest.json`

## Network

n8n is expected to run on the same VPS / Docker network.
The API target used by the workflows is `http://api:8000`.

## Rules

- n8n does not store business data.
- n8n does not decide segmentation or campaign state.
- Retries belong in n8n only for transport-level failures.
- All scoring, enrollment, branching, and conversation logic remain in FastAPI.

## MCP

`MCP_SETUP.md` explains how to connect the n8n instance to Codex through n8n's instance-level MCP server, based on the official n8n docs and blog.
