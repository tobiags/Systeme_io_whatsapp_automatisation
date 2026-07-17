from dataclasses import dataclass, field


@dataclass
class JourneyStep:
    step_key: str
    template_key: str
    # 3-way branching based on StreamYard state for the PRIOR day:
    #   (1) contact attended live         → template_key (main)
    #   (2) registered but didn't attend  → registered_absent_template_key
    #   (3) never registered              → no_show_template_key
    registered_absent_template_key: str | None = field(default=None)
    no_show_template_key: str | None = field(default=None)
    # ScoreEvent that proves live attendance for the prior day
    attendance_event: str | None = field(default=None)
    # ScoreEvent that proves StreamYard registration (but maybe not attendance)
    registration_event: str | None = field(default=None)


# ── Journey (9 steps, 18 templates) ─────────────────────────────────────────
#
# PHASE 1 — Pre-challenge (immediate + J-1)
#   WELCOME triggers on Systeme.io signup (immediate).
#   COUNTDOWN_J1 sends the day before the challenge starts.
#
# PHASE 2-4 — Live days 1-3 (3 templates each for days 2-3)
#   DAY_2 / DAY_3 use 3-way branching based on the prior day's StreamYard state:
#     • attended live          → main template (e.g. live_day2_attended_v1)
#     • registered but absent  → registered_absent_template_key
#     • never registered       → no_show_template_key
#
# PHASE 5 — Post-challenge follow-up (4 steps, all MARKETING)
#   AFTER_REPLAY J+1 · AFTER_1 J+2 · AFTER_2 J+3 · AFTER_3 J+4
#
# Timed reminders (not in journey, fired by _dispatch_timed_reminders):
#   H-10 J1/J2/J3 + H-2 J3 + H+90 J3 (MARKETING offer)

DEFAULT_JOURNEY = [
    # ── Phase 1 — Pre-challenge ──────────────────────────────────────────────
    JourneyStep(step_key="WELCOME",      template_key="welcome_v1"),
    JourneyStep(step_key="COUNTDOWN_J1", template_key="countdown_j1_v1"),
    # ── Phase 2 — Day 1 ─────────────────────────────────────────────────────
    JourneyStep(step_key="DAY_1",        template_key="live_day1_v1"),
    # ── Phase 3 — Day 2 (3-way branch on day1 state) ────────────────────────
    JourneyStep(
        step_key="DAY_2",
        template_key="live_day2_attended_v1",
        registered_absent_template_key="live_day2_registered_absent_v1",
        no_show_template_key="live_day2_not_registered_v1",
        attendance_event="day1_live_joined",
        registration_event="day1_streamyard_registered",
    ),
    # ── Phase 4 — Day 3 (3-way branch on day2 state) ────────────────────────
    JourneyStep(
        step_key="DAY_3",
        template_key="live_day3_attended_v1",
        registered_absent_template_key="live_day3_registered_absent_v1",
        no_show_template_key="live_day3_not_registered_v1",
        attendance_event="day2_live_joined",
        registration_event="day2_streamyard_registered",
    ),
    # ── Phase 5 — Post-challenge ─────────────────────────────────────────────
    # AFTER_REPLAY: J+1 replay link (48h window) — MARKETING
    JourneyStep(step_key="AFTER_REPLAY", template_key="post_replay_v1"),
    # AFTER_1: J+2 booking / exchange link — MARKETING
    JourneyStep(step_key="AFTER_1",      template_key="post_testimonials_v1"),
    # AFTER_2: J+3 pre-closer message — MARKETING
    JourneyStep(step_key="AFTER_2",      template_key="post_closer_v1"),
    # AFTER_3: J+4 closer booking call — MARKETING
    JourneyStep(step_key="AFTER_3",      template_key="post_closer_call_v1"),
]


# ── Smart-skip helper ─────────────────────────────────────────────────────────

# Only J-1 countdown remains (WELCOME always sent, never skipped).
_COUNTDOWN_STEPS = [
    "COUNTDOWN_J1",
]


def compute_start_step(days_until_challenge: int) -> str:
    """Return the first journey step a late registrant should start at.

    Logic:
      days_until_challenge ≥ 7  → WELCOME (normal, full sequence)
      days_until_challenge > 1  → WELCOME (welcome now, wait for J-1)
      days_until_challenge == 1 → WELCOME (only J1 countdown left)
      days_until_challenge == 0 → DAY_1 (challenge is today, skip all countdowns)
      days_until_challenge < 0  → DAY_1 (challenge already started)

    WELCOME is always sent (it's the opt-in confirmation).
    The caller is responsible for advancing to the right countdown step
    after the welcome is delivered (see enroll_contact in main.py).
    """
    if days_until_challenge <= 0:
        return "DAY_1"
    step_key = f"COUNTDOWN_J{days_until_challenge}"
    if step_key in _COUNTDOWN_STEPS:
        return step_key
    # More than 6 days left → start from WELCOME, full sequence
    return "WELCOME"
