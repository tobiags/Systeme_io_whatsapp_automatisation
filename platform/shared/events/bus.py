from shared.contracts.events import DomainEvent

_handlers: dict[str, list] = {}


def subscribe(event_name: str, handler):
    _handlers.setdefault(event_name, []).append(handler)


def publish(event: DomainEvent):
    for handler in _handlers.get(event.name, []):
        handler(event)
