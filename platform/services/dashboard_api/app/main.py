from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.orm import Session

from shared.db.session import get_db
from services.dashboard_api.app.read_models import get_dashboard_summary

router = APIRouter(prefix="/dashboard")


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return get_dashboard_summary(db)


app = FastAPI()
app.include_router(router)
