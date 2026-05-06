from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import Contact
from shared.db.session import get_db

router = APIRouter(prefix="/contacts")


class CreateContact(BaseModel):
    phone: str
    first_name: str | None = None
    source: str


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contact(payload: CreateContact, db: Session = Depends(get_db)):
    contact = Contact(
        id=f"ct_{uuid4().hex[:8]}",
        phone=payload.phone,
        first_name=payload.first_name,
        source=payload.source,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return {"id": contact.id, "phone": contact.phone, "first_name": contact.first_name, "source": contact.source}


app = FastAPI()
app.include_router(router)
