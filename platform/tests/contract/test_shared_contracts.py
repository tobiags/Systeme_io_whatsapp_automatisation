from shared.contracts.contact import ContactUpsert
from shared.contracts.events import DomainEvent


def test_contact_upsert_contract():
    payload = ContactUpsert(phone="+22900000000", first_name="Ada", source="systemeio")
    assert payload.phone.startswith("+")
    assert payload.source == "systemeio"


def test_domain_event_contract():
    event = DomainEvent(name="contact.created", aggregate_id="c_123", payload={"source": "systemeio"})
    assert event.name == "contact.created"
