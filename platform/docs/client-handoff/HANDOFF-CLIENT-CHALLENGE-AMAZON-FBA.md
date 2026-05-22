# Client Handoff - Challenge Amazon FBA (WhatsApp Automation)

## 1. Purpose

This document is the client-facing handoff for the WhatsApp automation system built for the Amazon FBA live challenge.

It explains:

- what has been delivered
- how to operate the system end-to-end (scaffolding method)
- which links and credentials are required (without exposing secrets publicly)
- what to do before / during / after each live
- how to validate everything with a minimal test
- scaling options (retainer roadmap)

---

## 2. What Has Been Delivered

### 2.1 Business outcomes

- Leads are captured from Systeme.io funnels and routed into the platform.
- Contacts are enrolled into the correct cohort (EU / US-CA).
- WhatsApp messages are sent via Wati using approved templates.
- Attendance/registration signals drive branching for Day 2/Day 3 and post-live follow-ups.
- Messages stop automatically after a purchase signal is recorded.
- A StreamYard operator portal ("PILOTAGE LIVE") allows running the live workflow without SSH/curl.

### 2.2 Key components

- WhatsApp messaging provider: Wati (WhatsApp Business)
- Lead source: Systeme.io funnels (EU + US/CA)
- Orchestration: n8n workflows
- Platform services: API + scheduling + scoring + consent + campaign logic
- Operator UI:
  - Admin Console (dashboard)
  - StreamYard Ops Portal ("PILOTAGE LIVE")

---

## 3. Definitions (Quick Glossary)

- Cohort:
  - `EU` (Paris time)
  - `US-CA` (Montreal time)
- Edition key: a unique identifier for a challenge edition, used to store per-day live links.
  - Example: `2026-05-21-usca`
- Day number:
  - `1`, `2`, `3` (live session day)
- StreamYard states:
  - attended live
  - registered but absent
  - not registered
- Wati template: a WhatsApp-approved message template with placeholders `{{1}}`, `{{2}}`, ...

---

## 4. Required Links (Fill-in Section)

Provide these values to the operator team.

### 4.1 Admin Console (Dashboard)

- URL: `http://whatsapp.178.104.229.163.nip.io:3001/`

### 4.2 StreamYard Ops Portal (PILOTAGE LIVE)

- URL (tokenized): `http://whatsapp.178.104.229.163.nip.io:3001/ops/streamyard?token=ops_streamyard_2026_fba_client_x9K4mP2qL7zR`
  - This link must be kept private.

### 4.3 Wati

- Wati workspace: `<WATI_WORKSPACE_NAME>`
- WhatsApp business number connected in Wati: `<WATI_NUMBER>`

### 4.4 Payment + Booking + Replays

- Payment page URL (Day 3 offer): `A RENSEIGNER`
- Booking link (closer call): `A RENSEIGNER`
- Replay Day 1 URL: `A RENSEIGNER`
- Replay Day 2 URL: `A RENSEIGNER`
- Replay Day 3 URL: `A RENSEIGNER`

Where these URLs are used:

- Payment URL is injected into the Day 3 offer template (`live_day3_offer_hplus2`) as `{{2}}`.
- Booking URL is injected into `post_closer_call` and `post_recap_attended` as `{{2}}`.
- Replay URLs are injected into:
  - `post_recap_registered_absent` (`{{2}}`, `{{3}}`, `{{4}}`)
  - `post_recap_not_registered` (`{{2}}`, `{{3}}`, `{{4}}`)

Notes:
- These links are configured directly in the `PILOTAGE LIVE` portal, for the relevant edition.
- You can go live without replays configured (post-live recap will not contain links yet), but payment + closer booking should be configured before Day 3.

---

## 5. Templates (Wati)

### 5.1 Template rules

- Category: Marketing
- Language: French
- No buttons (unless explicitly requested later)
- Placeholders: `{{1}}`, `{{2}}`, `{{3}}`, `{{4}}`
- Always provide sample content when creating templates

### 5.2 Expected template set

The platform expects the Wati template keys already created and aligned, including (non-exhaustive):

- `welcome`
- `countdown_j6` ... `countdown_j1`
- `live_day1`, `live_day1_h10`, `live_day1_hplus5`
- `live_day2_attended_v2`, `live_day2_registered_absent`, `live_day2_not_registered`, `live_day2_h10`, `live_day2_hplus5`
- `live_day3_attended_v2`, `live_day3_registered_absent`, `live_day3_not_registered`, `live_day3_h10`, `live_day3_hplus5`
- `live_day3_offer_hplus2`
- `post_recap_attended`, `post_recap_registered_absent`, `post_recap_not_registered`
- `post_inaction_reason`
- `post_closer_call`
- `post_testimonials` (optional, only when filled with real testimonials)

---

## 6. Operating the System (Scaffolding Method)

This section is written so the client can execute without technical support.

### Step 1 - Confirm Wati is ready

1. Open Wati.
2. Confirm the WhatsApp Business number is connected and "online".
3. Confirm required templates are approved/available.

Validation:
- Send a manual test template (`welcome`) to a test number (not the business number itself).

### Step 2 - Confirm Systeme.io funnels are connected

For each active funnel (EU / US-CA):

1. Open Systeme.io funnel step (opt-in page).
2. Open Automation Rules.
3. Ensure a webhook action is configured (do not remove existing tracking rules).

Validation:
- Submit a test opt-in.
- Confirm a WhatsApp `welcome` arrives.

### Step 3 - Create/verify StreamYard lives

For each cohort (EU / US-CA) and each day (1..3):

1. Create/verify the StreamYard live.
2. Copy the watch/join URL.

Validation:
- The operator can paste the URL into the PILOTAGE LIVE portal.

### Step 4 - Use PILOTAGE LIVE (Before / During / After)

#### 4.A Before the live (mandatory)

1. Open PILOTAGE LIVE portal.
2. Select cohort.
3. Fill `edition_key` and `day_number`.
4. Paste the StreamYard live URL.
5. Click "Enregistrer le live".

Outcome:
- All reminders for that day use the correct live link.

#### 4.A bis Configure edition links (mandatory before offer/replay messages)

1. Stay on the same `PILOTAGE LIVE` portal.
2. Keep the correct cohort + `edition_key`.
3. Fill:
   - payment link
   - closer / booking link
   - replay day 1
   - replay day 2
   - replay day 3
4. Click "Enregistrer les liens".

Outcome:
- Day 3 offer messages use the correct payment page.
- Post-live recap messages use the correct replay links.
- Booking / closer messages use the correct reservation link.

#### 4.B Just before / at the start (recommended)

1. Export or gather StreamYard registrants.
2. Paste numbers (one per line) or import CSV.
3. Click "Envoyer les inscrits".

Outcome:
- The system can branch follow-ups (registered-absent vs not-registered).

#### 4.C After the live (mandatory)

1. Export or gather attendees.
2. Paste numbers or import CSV.
3. Click "Envoyer les presents".

Outcome:
- The system branches Day 2/Day 3/post-live messages correctly.

### Step 5 - Daily monitoring

1. Check Wati inbox for replies.
2. Respond manually when needed (or assign to closers).
3. Check Admin Console for:
   - contact count
   - message count
   - human follow-up queue

---

## 7. What To Do If Something Looks Wrong

### WhatsApp message not sent

Checklist:

1. Is the number connected in Wati?
2. Is the template approved in Wati (same name as the system expects)?
3. Is the contact opted-in (consent)?
4. Was the live URL registered in PILOTAGE LIVE for that day/cohort?

### Wrong link in reminders

1. Open PILOTAGE LIVE.
2. Re-submit the live URL for the correct cohort/day.

### Wrong payment / closer / replay link

1. Open PILOTAGE LIVE.
2. Keep the correct `edition_key`.
3. Update the affected link in the "Liens de vente et replay" section.
4. Click "Enregistrer les liens" again.

### Branching seems incorrect (present vs absent)

1. Confirm registrants were sent.
2. Confirm attendees were sent after the live.

---

## 8. Advantages / Why This System Works

- Faster lead response times on WhatsApp.
- Higher live attendance via structured reminders.
- Reduced manual workload (ops portal replaces technical steps).
- More relevant messaging via behavioral branching.
- Cleaner pipeline for closers (human follow-up only where needed).
- Automatic suppression after purchase to avoid over-messaging buyers.

---

## 9. Scaling Options (Retainer Roadmap)

This platform is designed to scale. A retainer allows continuous optimization and conversion improvements.

### Option A - Conversion optimization (monthly)

- Template iteration based on performance.
- Better timing rules per cohort.
- A/B tests on follow-up sequences.
- Better segmentation rules (cold/warm/hot).
- Replay distribution improvements.

Benefit:
- More attendance + higher conversion without increasing ad spend.

### Option B - Reduced manual ops (monthly)

- Semi-automation of StreamYard exports (CSV import templates, Zapier, or alternative tooling).
- Operator QA checks and alerting.
- "Did we forget to submit registrants/attendees?" reminders.

Benefit:
- Less risk of human error and smoother execution per live.

### Option C - Sales enablement (monthly)

- Closer dashboard improvements.
- Lead summaries and objection tracking.
- Priority scoring for fastest callbacks.

Benefit:
- Higher close rate with fewer wasted calls.

### Option D - Higher trust automation (monthly)

- Persistent memory per lead (structured contact memory).
- Safer, more consistent tone and fewer repetitions.
- Better handoff notes to humans.

Benefit:
- Better experience and increased trust, especially across multi-day conversations.

---

## 10. Next Steps (Go-Live Checklist)

- Confirm Wati templates are approved and match the expected keys.
- Confirm payment URL, booking URL, and replay URLs are filled in `PILOTAGE LIVE` for the active edition.
- Confirm both funnels (EU/US-CA) fire webhooks correctly.
- Confirm PILOTAGE LIVE is accessible and tested.
- Run one supervised live execution, then switch to autonomous mode.

