from shared.contracts.events import DomainEvent

_EVENT_STORE: list[dict] = []


def append(event: DomainEvent) -> None:
    _EVENT_STORE.append(event.model_dump())


def all_events() -> list[dict]:
    return list(_EVENT_STORE)


def events_for(aggregate_id: str) -> list[dict]:
    return [e for e in _EVENT_STORE if e["aggregate_id"] == aggregate_id]
