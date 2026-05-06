from services.messaging.app.providers.base import MessagingProvider


class Dialog360Provider(MessagingProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        # TODO: implement real 360dialog API call
        return {
            "provider": "360dialog",
            "provider_message_id": f"360_{contact_id}",
            "status": "queued",
            "template_key": template_key,
        }
