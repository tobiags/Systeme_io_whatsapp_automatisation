from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    name: str
    aggregate_id: str
    payload: dict
    version: int = Field(default=1)
