from abc import ABC, abstractmethod


class MessagingProvider(ABC):
    @abstractmethod
    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        raise NotImplementedError

    @abstractmethod
    def send_text(self, contact_id: str, text: str) -> dict:
        raise NotImplementedError
