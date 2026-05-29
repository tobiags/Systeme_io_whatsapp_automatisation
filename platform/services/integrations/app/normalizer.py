def _normalize_phone(raw: str | None) -> str | None:
    """Normalize a phone number to digits-only international format (no leading + or 00).

    Handles:
      +33612345678  → 33612345678
      0033612345678 → 33612345678
      33612345678   → 33612345678  (already clean)
      spaces / dashes stripped
    """
    if not raw:
        return None
    import re
    phone = re.sub(r"[\s\-\.\(\)]", "", raw.strip())
    if phone.startswith("+"):
        return phone[1:]
    if phone.startswith("00"):
        return phone[2:]
    return phone or None


def normalize_systemeio(payload: dict) -> dict:
    """
    Normalize a Systeme.io webhook payload to our internal format.

    Supported shapes:

    1. Legacy flat format:
       {
         "email": "john@example.com",
         "phone_number": "33600000001",
         "first_name": "John"
       }

    2. Direct Systeme.io webhook:
       {
         "contact": {
           "email": "john@example.com",
           "fields": [
             {"slug": "first_name", "value": "John"},
             {"slug": "phone_number", "value": "33600000001"}
           ]
         }
       }

    3. n8n-forwarded Systeme.io webhook:
       {
         "body": {
           "data": {
             "contact": {
               "email": "john@example.com",
               "fields": {
                 "first_name": "John",
                 "phone_number": "33600000001"
               }
             }
           }
         }
       }
    """
    body = payload.get("body")
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, dict) and isinstance(data.get("contact"), dict):
            payload = data

    contact_obj = payload.get("contact")

    if isinstance(contact_obj, dict):
        email = contact_obj.get("email")
        raw_fields = contact_obj.get("fields") or []
        if isinstance(raw_fields, list):
            fields_by_slug = {field.get("slug"): field.get("value") for field in raw_fields}
        elif isinstance(raw_fields, dict):
            fields_by_slug = raw_fields
        else:
            fields_by_slug = {}

        phone = _normalize_phone(fields_by_slug.get("phone_number") or fields_by_slug.get("phone"))
        first_name = fields_by_slug.get("first_name")
        last_name = fields_by_slug.get("last_name") or fields_by_slug.get("surname")
    else:
        email = payload.get("email")
        phone = _normalize_phone(payload.get("phone_number") or payload.get("phone"))
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
