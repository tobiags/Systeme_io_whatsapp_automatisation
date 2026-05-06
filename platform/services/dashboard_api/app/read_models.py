from dataclasses import dataclass, field


@dataclass
class DashboardSummary:
    contacts_total: int = 0
    campaigns_active: int = 0
    manual_followups: int = 0
    conversion_rate: float = 0.0
    contacts_by_segment: dict = field(default_factory=lambda: {
        "froid": 0, "tiede": 0, "chaud": 0, "tres_chaud": 0
    })
    contacts_by_cohort: dict = field(default_factory=lambda: {
        "EU": 0, "US-CA": 0
    })
