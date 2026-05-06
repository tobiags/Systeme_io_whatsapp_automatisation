from services.messaging.app.providers.base import MessagingProvider


class WatiProvider(MessagingProvider):
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url
        self.api_token = api_token

    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        # TODO: implement real Wati API call
        return {
            "provider": "wati",
            "provider_message_id": f"wati_{contact_id}",
            "status": "queued",
            "template_key": template_key,
        }
