from fastapi import FastAPI

from services.dashboard_api.app.read_models import DashboardSummary

app = FastAPI()


@app.get("/dashboard/summary")
def dashboard_summary():
    summary = DashboardSummary()
    return {
        "contacts_total": summary.contacts_total,
        "campaigns_active": summary.campaigns_active,
        "manual_followups": summary.manual_followups,
        "conversion_rate": summary.conversion_rate,
        "contacts_by_segment": summary.contacts_by_segment,
        "contacts_by_cohort": summary.contacts_by_cohort,
    }
