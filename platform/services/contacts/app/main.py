from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.db.models import Contact, ContactScore
from shared.db.session import get_db

router = APIRouter(prefix="/contacts")


class CreateContact(BaseModel):
    phone: str
    first_name: str | None = None
    source: str


def _contact_dict(c: Contact) -> dict:
    return {"id": c.id, "phone": c.phone, "first_name": c.first_name, "source": c.source}


@router.get("")
def list_contacts(db: Session = Depends(get_db)):
    """Return all contacts, newest first."""
    contacts = db.query(Contact).order_by(Contact.created_at.desc()).all()
    return [_contact_dict(c) for c in contacts]


@router.post("", status_code=status.HTTP_201_CREATED)
def upsert_contact(payload: CreateContact, response: Response, db: Session = Depends(get_db)):
    """Create contact or update if phone already exists (upsert)."""
    existing = db.query(Contact).filter(Contact.phone == payload.phone).first()
    if existing:
        if payload.first_name:
            existing.first_name = payload.first_name
        existing.source = payload.source
        db.commit()
        db.refresh(existing)
        response.status_code = status.HTTP_200_OK
        return _contact_dict(existing)

    contact = Contact(
        id=f"ct_{uuid4().hex[:8]}",
        phone=payload.phone,
        first_name=payload.first_name,
        source=payload.source,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _contact_dict(contact)


@router.get("/{contact_id}/score")
def get_contact_score(contact_id: str, db: Session = Depends(get_db)):
    """Return the running engagement score total for a contact."""
    contact_score = (
        db.query(ContactScore)
        .filter(ContactScore.contact_id == contact_id)
        .first()
    )
    total = contact_score.total_score if contact_score else 0
    return {"contact_id": contact_id, "total_score": total}


@router.get("/{contact_id}")
def get_contact(contact_id: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _contact_dict(contact)


app = FastAPI()
app.include_router(router)
