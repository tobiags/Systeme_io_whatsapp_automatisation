from services.campaigns.app.rules import DEFAULT_JOURNEY, JourneyStep


def get_next_step(enrollment: dict) -> JourneyStep:
    return DEFAULT_JOURNEY[0]
