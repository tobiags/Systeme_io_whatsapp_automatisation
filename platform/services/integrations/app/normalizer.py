def normalize_systemeio(payload: dict) -> dict:
    """
    Normalize a Systeme.io webhook payload to our internal format.

    Systeme.io sends two shapes depending on the event type:

    1. Real webhook (contact.created / optin) — Context7 / developer.systeme.io:
       {
         "contact": {
           "id": 12345,
           "email": "john@example.com",
           "fields": [
             {"slug": "first_name",   "value": "John"},
             {"slug": "phone_number", "value": "33600000001"}
           ]
         }
       }

    2. Flat legacy / test payload (used in tests and some custom automations):
       {
         "email": "john@example.com",
         "phone_number": "33600000001",
         "first_name": "John"
       }

    Both shapes are supported; real Systeme.io format takes priority.
    """
    contact_obj = payload.get("contact")

    if isinstance(contact_obj, dict):
        # ── Real Systeme.io webhook format ────────────────────────────────────
        email = contact_obj.get("email")
        # Fields is an array: [{"slug": "...", "value": "..."}]
        fields: list[dict] = contact_obj.get("fields") or []
        fields_by_slug = {f.get("slug"): f.get("value") for f in fields}
        phone = fields_by_slug.get("phone_number") or fields_by_slug.get("phone")
        first_name = fields_by_slug.get("first_name")
        last_name = fields_by_slug.get("last_name") or fields_by_slug.get("surname")
    else:
        # ── Flat legacy format (tests / custom automations) ───────────────────
        email = payload.get("email")
        phone = payload.get("phone_number") or payload.get("phone")
        first_name = payload.get("first_name")
        last_name = payload.get("last_name")

    return {
        "event_name": "lead.captured",
        "payload": {
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "source": "systemeio",
        },
    }
