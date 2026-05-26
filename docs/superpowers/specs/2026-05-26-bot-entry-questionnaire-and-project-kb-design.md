# Bot Entry Questionnaire And Project KB Design

## Objective

Stabilize the WhatsApp bot's first conversation turn so real leads do not fall into clarification loops, dead-end replies, or off-topic AI improvisation.

This design introduces:

1. a strict entry questionnaire in the first welcome interaction
2. a project-specific knowledge base used before any generic AI reasoning
3. a bounded fallback flow for ambiguous or messy lead messages

The goal is to make the bot reliable on real WhatsApp inputs, not only on clean demo phrases.

## Problem Statement

Recent real conversations show recurring failure modes:

- a lead answers the opening question correctly in free text (`Aucune experience en vente en ligne`) and the bot replies `Tu peux preciser ?`
- a lead sends greetings plus a useful answer in the same message and the bot ignores the useful part
- small corrections (`Pars`) or noisy replies (`OK c'est compris`) cause repeated soft-open loops
- FAQ-style questions after an opening exchange are not always recovered cleanly
- OpenAI fallback can still produce behavior that is locally "valid" but wrong for this project

The current system is still too open-ended at the start of the conversation.

## Scope

This design changes only the bot entry flow and its answer routing.

In scope:

- the first welcome template text
- how the first lead reply is interpreted
- how entry-state memory is stored
- how project rules are retrieved before AI fallback
- how ambiguity, reformulation, and human escalation work

Out of scope:

- broad redesign of daily campaign messages
- pricing or sales-stage strategy after J3
- unrelated cleanup of existing prompts or docs

## Recommended Approach

Use a guided entry questionnaire plus project KB retrieval.

The bot should no longer start by asking an open free-text question such as:

`tu pars de zero, ou tu as deja commence a vendre en ligne ?`

Instead, it should ask the lead to reply with one of three numbers:

- `1` = beginner
- `2` = already started selling online
- `3` = question about the challenge

If the lead replies in free text anyway, the bot should try to map that text into one of those three buckets.

If the bot still cannot map the message reliably:

- it reformulates once
- then escalates to human if the next reply is still off-track

This keeps the opening simple while preserving flexibility for real-world lead phrasing.

## Entry Message Design

Replace the current first template body with:

`Bonjour {first_name}, ravi de t'avoir avec nous pour le Challenge Amazon FBA.`

`Pour que je t'oriente correctement, reponds juste avec un chiffre :`

`1 = je pars de zero`
`2 = j'ai deja commence a vendre en ligne`
`3 = j'ai surtout une question sur le challenge`

Constraints:

- keep the message short
- no open-ended question in the first turn
- no extra marketing copy in the questionnaire block
- no second question in the same message

## Conversation State

The system should store a minimal script state on the welcome / first session reply so later inbound handling knows where the lead is in the entry flow.

Suggested state shape:

```json
{
  "flow": "entry_questionnaire",
  "stage": "awaiting_choice",
  "rephrase_count": 0
}
```

Possible states:

- `awaiting_choice`
- `choice_captured`
- `rephrased_once`
- `entry_escalated`

The state must be enough to decide whether to:

- process a valid choice
- interpret free text
- reformulate once
- stop and escalate

## Project Knowledge Base

The system should maintain a local project KB that acts as the source of truth for what the bot is allowed to say.

This KB must be consulted before generic OpenAI fallback.

### KB sections

#### 1. Entry questionnaire rules

- valid numeric choices: `1`, `2`, `3`
- mapped meaning of each choice
- allowed reply for each choice

#### 2. Entry free-text mapping

Map common real-world phrases into questionnaire buckets.

Bucket `1` examples:

- `aucune experience`
- `aucune experience en vente en ligne`
- `je pars de zero`
- `je part de zero`
- `de zero`
- `de zer0`
- `debutant`
- `je commence`
- `je n'ai pas encore commence`

Bucket `2` examples:

- `j'ai deja commence`
- `je vends deja`
- `je faisais la vente en ligne`
- `j'ai une boutique`
- `je suis deja lance`
- `je vendais deja`

Bucket `3` examples:

- `comment ca marche`
- `c'est quoi le challenge`
- `horaire`
- `lien`
- `comment participer`
- `comment se passe le challenge`

#### 3. FAQ allowed

Only authorized self-service topics:

- challenge format and functioning
- live schedule
- participation link

#### 4. Restricted topics

The bot must not improvise on:

- price
- payment terms
- product choice coaching
- result promises
- sales pressure before allowed phase

#### 5. Human escalation rules

Immediate escalation for:

- call request
- explicit buying intent
- payment problem
- strong objection
- complaint
- refund
- complex personal situation

#### 6. Conversation guardrails

- no repeated `N'hesite pas...` loop
- no `Tu peux preciser ?` if the lead is obviously answering the opening script
- only one reformulation in the entry flow
- if the lead signals confusion about the bot's previous reply, do not repeat the same fallback

## Routing Order

The routing order must be deterministic.

### Step 1. Human escalation detection

If the message matches an immediate escalation rule, escalate now.

### Step 2. Entry questionnaire state

If the lead is in the entry questionnaire flow:

1. check if the reply is exactly `1`, `2`, or `3`
2. if not, try KB free-text mapping
3. if still unresolved and `rephrase_count == 0`, send one reformulation
4. if still unresolved after reformulation, escalate human

### Step 3. FAQ KB

If the message clearly matches an allowed FAQ, answer from project KB.

### Step 4. Restricted-topic KB

If the topic is restricted, send the approved bounded response or escalate if required.

### Step 5. OpenAI constrained fallback

Only after all previous checks:

- OpenAI may help phrase the reply
- but only inside the project KB constraints
- OpenAI is not allowed to invent a new allowed topic

### Step 6. Final fallback

If the system still cannot safely classify the message:

- if this is the first ambiguity inside the entry flow, reformulate once
- otherwise escalate human

## Reply Behavior By Choice

### Choice 1: Beginner

Intent:

- `entry_choice_beginner`

Allowed reply shape:

- short acknowledgment
- reassurance
- no extra qualification question

Example:

`Merci pour ton retour. Le challenge est justement prevu pour repartir sur des bases claires et t'aider a avancer pas a pas.`

### Choice 2: Already started

Intent:

- `entry_choice_started`

Allowed reply shape:

- short acknowledgment
- signal that the challenge will help structure and clarify
- no sales push

Example:

`Merci pour ton retour. Le challenge va justement t'aider a remettre les points essentiels dans le bon ordre pour avancer plus proprement.`

### Choice 3: Challenge question

Intent:

- `entry_choice_question`

Allowed reply shape:

- open FAQ handling
- answer from authorized KB if possible

Example:

`Bien recu. Pose-moi ta question sur le challenge et je te reponds directement.`

## Reformulation Rule

If the lead does not answer with `1`, `2`, or `3`, and the free-text mapping is not reliable enough:

Send exactly one reformulation:

`Reponds juste avec 1, 2 ou 3 pour que je te reponde correctement.`

No second reformulation.

If the lead still replies with unrelated or incoherent text after this:

- escalate human
- do not send another clarification loop

## OpenAI Role

OpenAI remains useful, but with a reduced role.

OpenAI should not decide what the bot is allowed to say.

Instead:

- local KB decides the allowed topic and response boundaries
- OpenAI may help phrase a reply cleanly if the case is ambiguous but still within an allowed category

Rule:

`KB decides the content boundary; OpenAI only helps with wording inside that boundary.`

## Expected Impact On Known Failures

### `Aucune experience en vente en ligne`

Expected behavior:

- maps to choice `1`
- no clarification fallback

### `Bonjour Alban. Je pars de zero`

Expected behavior:

- mixed greeting + answer still maps to choice `1`

### `Enchante Alban`

Expected behavior:

- does not trigger `Tu peux preciser ?`
- if no choice can be inferred yet, send the single entry reformulation

### `Je faisais la vente en ligne etant en Cote d'Ivoire...`

Expected behavior:

- maps to choice `2`
- short acknowledgment reply

### `Pars`

Expected behavior:

- if it immediately follows a malformed beginner message, interpret as correction if confidence is sufficient
- otherwise do not loop endlessly; use reformulation or escalate

### `OK c'est compris`

Expected behavior:

- no repeated clarification
- no repeated `N'hesite pas...` loop

## Testing Requirements

Add regression coverage for:

- exact numeric choices `1`, `2`, `3`
- mixed greeting + choice-like answer
- beginner free-text variants
- started-selling free-text variants
- challenge-question free-text variants
- one-time reformulation behavior
- second off-track reply causes human escalation
- no repeated `N'hesite pas...` after acknowledgment loops
- no `Tu peux preciser ?` when the lead is answering the entry flow

Test layers:

- conversation AI unit / e2e tests
- Wati inbound integration tests
- at least one stateful conversation test for reformulation and escalation

## Risks

### Risk: too much rigidity

If the entry flow is too strict, some leads may feel constrained.

Mitigation:

- keep free-text interpretation as a secondary path
- reformulate once before escalation

### Risk: stale KB

New lead phrasing will keep appearing.

Mitigation:

- maintain the KB from real conversation transcripts
- add regression tests for each repeated new pattern

### Risk: OpenAI still leaks outside guardrails

Mitigation:

- only use OpenAI after deterministic KB routing
- keep restricted topics out of the AI-authorized path

## Implementation Notes

Likely touched areas:

- welcome template generation / storage
- conversation AI normalization and KB routing
- inbound script-state handling in integrations
- regression tests for stateful opening conversations

No broader refactor is required for this change.

