# Bot Guardrails System

This document explains how the WhatsApp bot is intentionally structured so a
future coding session can continue the work without rediscovering the same
pitfalls.

## Why this exists

The bot failed in production for recurring reasons:

- short real-world answers like `0`, `zero`, `de zero`
- vague gratitude messages like `merci`, `super merci`
- soft interest like `j'aimerais apprendre`
- natural FAQ wording like `ca se passe comment le challenge`
- clarification loops that made the bot feel robotic

The fix is not "more prompt". The fix is:

1. deterministic routing first
2. local knowledge retrieval for repeated production phrasing
3. only then generic fallback

## Current routing order

The effective order in `platform/services/conversation_ai/app/service.py` is:

1. `needs_human_escalation(...)`
2. `_knowledge_base_reply(...)`
3. signal-level routing:
   - `escalate`
   - `acquittal`
   - `interest`
4. self-service FAQ lookup
5. restricted topic handlers
6. clarification / safe fallback

This order matters.

Do not move the knowledge base behind the generic fallback unless you want the
same old production misses to come back.

## Knowledge base source of truth

The local retrieval layer lives in:

- `platform/services/conversation_ai/app/knowledge_base.py`

It is deliberately simple:

- ordered list of rules
- `exact_messages` for short or fragile inputs
- `keywords` for recurring phrasing families
- per-rule `intent`, `reply`, `needs_human`
- optional `script_state` when a rule is allowed to open one follow-up

## Rule categories we currently support

### 1. Restricted beginner declarations

Examples:

- `0`
- `zero`
- `de zero`
- `je part de zero`
- `je commence de zero`

These must not fall into acquittal.

Expected behavior:

- short reassurance
- no sales push
- no follow-up question

### 2. Explicit interest

Examples:

- `j'aimerais apprendre`
- `je veux en savoir plus`
- `ca m'interesse`
- `creer une boutique en ligne`

Expected behavior:

- exactly one follow-up question
- only on allowed subjects

### 3. Challenge overview FAQ

Examples:

- `ca se passe comment le challenge`
- `comment se passe le challenge`

Expected behavior:

- direct FAQ answer
- no clarification loop

### 4. Availability support

Examples:

- `je serai au boulot`
- `je ferai un effort pour ne pas rater le live`

Expected behavior:

- useful practical reply
- not a dead-end clarification

### 5. Soft acknowledgements

Examples:

- `merci`
- `merci alban`
- `super merci`

Expected behavior:

- soft open invitation
- never `tu peux preciser ta question`

## When to add a new KB rule

Add a rule when all three are true:

1. the phrasing has already appeared in a real lead conversation
2. generic routing handled it badly or weakly
3. the correct reply is stable and client-approved

Do not add a rule for a one-off curiosity.

## How to extend safely

1. Copy the exact real wording from production.
2. Normalize the wording to ASCII-compatible text.
3. Decide the category:
   - restricted topic
   - explicit interest
   - FAQ
   - availability
   - soft acknowledgement
   - escalate
4. Add the KB rule.
5. Add a regression test.
6. Run:
   - `python -m pytest platform/tests/e2e/test_conversation_ai_extended.py platform/tests/e2e/test_wati_inbound.py -q`
   - `python -m pytest platform/tests -q`

## What not to do

- do not solve repeated prod misses only with prompt edits
- do not route short answers like `0` through generic acquittal logic
- do not ask clarification after `merci`, `super`, `bien recu`
- do not let FAQ variants fall into `clarification_request`
- do not open multi-step scripts unless the client explicitly allows them

## If a future session resumes this project

Start by reading:

1. this file
2. `platform/services/conversation_ai/app/knowledge_base.py`
3. `platform/services/conversation_ai/app/service.py`
4. the latest transcript-based tests in:
   - `platform/tests/e2e/test_conversation_ai_extended.py`
   - `platform/tests/e2e/test_wati_inbound.py`

Then compare new production transcripts against the existing categories before
changing the routing.
