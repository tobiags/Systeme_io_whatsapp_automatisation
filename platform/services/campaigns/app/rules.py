from dataclasses import dataclass


@dataclass
class JourneyStep:
    step_key: str
    template_key: str


DEFAULT_JOURNEY = [
    JourneyStep(step_key="J-7", template_key="welcome_j7"),
    JourneyStep(step_key="J-6", template_key="content_j6"),
    JourneyStep(step_key="DAY_1", template_key="challenge_day_1"),
    JourneyStep(step_key="DAY_2", template_key="challenge_day_2"),
    JourneyStep(step_key="DAY_3", template_key="challenge_day_3"),
]
