import httpx

from services.messaging.app.providers.base import MessagingProvider


class WatiProvider(MessagingProvider):
    """Send WhatsApp template messages via Wati API."""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token

    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        params = [{"name": k, "value": v} for k, v in variables.items()]
        payload = {
            "template_name": template_key,
            "broadcast_name": f"{template_key}_{contact_id}",
            "receivers": [
                {
                    "whatsappNumber": contact_id,
                    "customParams": params,
                }
            ],
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.api_url}/api/v1/sendTemplateMessages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "provider": "wati",
                    "provider_message_id": data.get("id", f"wati_{contact_id}"),
                    "status": "queued",
                    "template_key": template_key,
                }
        except httpx.HTTPError as exc:
            # Log but don't crash — message is stored in DB with status queued
            return {
                "provider": "wati",
                "provider_message_id": f"wati_{contact_id}",
                "status": "failed",
                "template_key": template_key,
                "error": str(exc),
            }
