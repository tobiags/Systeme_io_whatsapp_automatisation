from services.messaging.app.providers.base import MessagingProvider


class MockProvider(MessagingProvider):
    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        return {
            "provider": "mock",
            "provider_message_id": f"msg_{contact_id}",
            "status": "queued",
            "template_key": template_key,
        }
