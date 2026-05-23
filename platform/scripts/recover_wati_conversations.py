import argparse
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config.settings import settings
from shared.db.models import InboundMessage
from shared.db.session import SessionLocal
from services.conversation_ai.app.prompts import BEGINNER_PROFILE_KEYWORDS, STARTED_PROFILE_KEYWORDS
from services.integrations.app.main import process_inbound_wati_message


def _contact_phone(contact: dict) -> str:
    for key in ("phone", "phoneNumber", "whatsappNumber", "waId"):
        value = contact.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "result", "contacts", "messages"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _message_text(message: dict) -> str:
    for key in ("text", "body", "messageText", "message", "conversationText"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            body = value.get("body")
            if isinstance(body, str) and body.strip():
                return body.strip()
    return ""


def _looks_like_user_message(message: dict) -> bool:
    for key in ("fromMe", "sentByMe", "isOwner", "isOutgoing", "outgoing"):
        value = message.get(key)
        if isinstance(value, bool):
            return not value

    marker = " ".join(
        str(message.get(key, "")).lower()
        for key in ("owner", "senderType", "type", "direction", "sentBy", "operatorName")
    )
    outbound_markers = ("agent", "operator", "outgoing", "sent", "owner", "bot")
    return not any(token in marker for token in outbound_markers)


def _is_recoverable_qualification(text: str) -> bool:
    normalized = text.lower().strip()
    keywords = BEGINNER_PROFILE_KEYWORDS + STARTED_PROFILE_KEYWORDS
    return any(keyword in normalized for keyword in keywords)


def _latest_recoverable_text(client: httpx.Client, phone: str) -> str | None:
    resp = client.get(
        f"{settings.wati_api_url}/api/v1/getMessages/{phone}",
        params={"pageSize": 10, "pageNumber": 1},
        headers={"Authorization": f"Bearer {settings.wati_api_token}"},
        timeout=15.0,
    )
    resp.raise_for_status()
    for message in _items(resp.json()):
        if not _looks_like_user_message(message):
            continue
        text = _message_text(message)
        if text and _is_recoverable_qualification(text):
            return text
    return None


def _iter_contact_phones(client: httpx.Client, page_size: int, max_pages: int):
    for page in range(1, max_pages + 1):
        resp = client.get(
            f"{settings.wati_api_url}/api/v1/getContacts",
            params={"pageSize": page_size, "pageNumber": page},
            headers={"Authorization": f"Bearer {settings.wati_api_token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        contacts = _items(resp.json())
        if not contacts:
            break
        for contact in contacts:
            phone = _contact_phone(contact)
            if phone:
                yield phone
        if len(contacts) < page_size:
            break


def main():
    parser = argparse.ArgumentParser(
        description="Catch up Wati conversations that answered the welcome prompt but never received an AI follow-up."
    )
    parser.add_argument("--apply", action="store_true", help="Actually send the catch-up replies.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of phones to scan.")
    parser.add_argument("--page-size", type=int, default=100, help="Wati contacts page size.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum Wati contact pages to inspect.")
    args = parser.parse_args()

    if not settings.wati_api_url or not settings.wati_api_token:
        raise SystemExit("WATI_API_URL / WATI_API_TOKEN must be configured.")

    scanned = 0
    recovered = 0

    with httpx.Client() as client:
        db = SessionLocal()
        try:
            for phone in _iter_contact_phones(client, args.page_size, args.max_pages):
                scanned += 1
                if scanned > args.limit:
                    break

                text = _latest_recoverable_text(client, phone)
                if not text:
                    continue

                already_logged = (
                    db.query(InboundMessage)
                    .filter(InboundMessage.phone == phone, InboundMessage.text == text)
                    .first()
                )
                if already_logged:
                    print(f"[skip] {phone} | already processed")
                    continue

                if not args.apply:
                    print(f"[dry-run] {phone} | {text}")
                    recovered += 1
                    continue

                result = process_inbound_wati_message(db, phone, text)
                print(
                    f"[sent] {phone} | intent={result['intent']} | status={result['delivery']['status']}"
                )
                recovered += 1
        finally:
            db.close()

    print(f"Scanned: {scanned} | Recoverable: {recovered}")


if __name__ == "__main__":
    main()
