from pydantic import BaseModel


class OutboundMessage(BaseModel):
    contact_id: str
    channel: str = "whatsapp"
    template_key: str
    variables: dict[str, str]
