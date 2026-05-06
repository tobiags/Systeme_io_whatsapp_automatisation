from pydantic import BaseModel


class ContactUpsert(BaseModel):
    phone: str
    first_name: str | None = None
    source: str
