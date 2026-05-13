# Behavioral Engagement Signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class support for behavior-driven engagement signals so the platform can ingest group join, link click, poll response, and reply-derived signals without waiting for WawPlus-specific integration.

**Architecture:** Introduce a generic engagement webhook in `integrations` that normalizes external signal aliases into scoring events, and enrich Wati inbound processing so meaningful prospect replies create conversational score events. Keep scoring centralized through existing `ScoreEvent`, `ContactScore`, and `Segment` patterns.

**Tech Stack:** FastAPI, SQLAlchemy, existing scoring service patterns, pytest.

---

### Task 1: Define behavior coverage in tests
- Add tests for a generic `/webhooks/engagement` endpoint that accepts phone or contact ID.
- Cover alias normalization (`group_joined` -> `group_whatsapp_joined`, `streamyard_clicked` -> `streamyard_link_clicked`).
- Cover zero-risk handling for unknown contacts and invalid events.
- Cover Wati inbound creating conversational score events when a real question is received.

### Task 2: Implement normalized engagement ingestion
- Add a request model and endpoint in `platform/services/integrations/app/main.py`.
- Reuse existing `_upsert_contact_score` path for score, segment, and event creation.
- Return structured counts to make n8n/WawPlus integration simple.

### Task 3: Enrich conversational scoring
- Add event types needed for engagement-based routing to `platform/services/scoring/app/rules.py`.
- Record a score event from `wati_inbound` when a contact sends a meaningful question.
- Keep the heuristic conservative to avoid inflating scores on trivial replies.

### Task 4: Verify and land
- Run targeted tests first.
- Run full `pytest` suite.
- Commit only the focused implementation changes.
