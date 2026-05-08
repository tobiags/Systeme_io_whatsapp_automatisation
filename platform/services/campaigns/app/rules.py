from dataclasses import dataclass, field


@dataclass
class JourneyStep:
    step_key: str
    template_key: str
    # If set, contacts who missed `attendance_event` receive this template instead.
    catchup_template_key: str | None = field(default=None)
    # ScoreEvent.event_type that proves attendance on the *prior* day.
    attendance_event: str | None = field(default=None)


DEFAULT_JOURNEY = [
    # Pre-challenge
    JourneyStep(step_key="J-7",    template_key="welcome_j7"),
    JourneyStep(step_key="J-6",    template_key="content_j6"),
    # Challenge days (J1-J3)
    JourneyStep(step_key="DAY_1",  template_key="challenge_day_1"),
    JourneyStep(
        step_key="DAY_2",
        template_key="challenge_day_2",
        catchup_template_key="challenge_day_2_catchup",
        attendance_event="day1_live_joined",
    ),
    JourneyStep(
        step_key="DAY_3",
        template_key="challenge_day_3",
        catchup_template_key="challenge_day_3_catchup",
        attendance_event="day2_live_joined",
    ),
    # Post-challenge (spec §3.5 — après challenge)
    JourneyStep(
        step_key="AFTER_1",
        template_key="post_challenge_recap",          # recap global + offre
        catchup_template_key="post_challenge_missed", # pour ceux qui ont tout raté
        attendance_event="day3_live_joined",
    ),
    JourneyStep(
        step_key="AFTER_2",
        template_key="post_challenge_followup",       # relance finale ou réinjection
    ),
]
