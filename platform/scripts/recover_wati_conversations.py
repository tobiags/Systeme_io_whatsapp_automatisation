import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.db.models import Contact, InboundMessage, Message
from shared.db.session import SessionLocal
from services.integrations.app.main import process_inbound_wati_message


def _iter_recoverable_inbounds(db, limit: int):
    rows = (
        db.query(InboundMessage)
        .order_by(InboundMessage.received_at.desc())
        .limit(limit * 10)
        .all()
    )

    seen_phones = set()
    recoverable: list[InboundMessage] = []
    for row in rows:
        if not row.phone or row.phone in seen_phones:
            continue

        contact_id = row.contact_id
        if not contact_id:
            normalized = row.phone.lstrip("+")
            contact = (
                db.query(Contact)
                .filter((Contact.phone == normalized) | (Contact.phone == f"+{normalized}"))
                .first()
            )
            contact_id = contact.id if contact else None

        has_followup = False
        if contact_id:
            has_followup = (
                db.query(Message)
                .filter(
                    Message.contact_id == contact_id,
                    Message.template_key == "ai_session_reply",
                    Message.created_at >= row.received_at,
                )
                .first()
                is not None
            )

        if has_followup:
            seen_phones.add(row.phone)
            continue

        # Ignore obviously empty / noise-only rows.
        if not (row.text or "").strip():
            seen_phones.add(row.phone)
            continue

        recoverable.append(row)
        seen_phones.add(row.phone)
        if len(recoverable) >= limit:
            break

    return recoverable


def main():
    parser = argparse.ArgumentParser(
        description="Catch up Wati conversations that answered the welcome prompt but never received an AI follow-up."
    )
    parser.add_argument("--apply", action="store_true", help="Actually send the catch-up replies.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of phones to scan.")
    parser.add_argument("--page-size", type=int, default=100, help="Wati contacts page size.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum Wati contact pages to inspect.")
    args = parser.parse_args()

    scanned = 0
    recovered = 0

    db = SessionLocal()
    try:
        for inbound in _iter_recoverable_inbounds(db, args.limit):
            scanned += 1

            if not args.apply:
                print(f"[dry-run] {inbound.phone} | {inbound.text}")
                recovered += 1
                continue

            result = process_inbound_wati_message(db, inbound.phone, inbound.text)
            print(
                f"[sent] {inbound.phone} | intent={result['intent']} | status={result['delivery']['status']}"
            )
            recovered += 1
    finally:
        db.close()

    print(f"Scanned: {scanned} | Recoverable: {recovered}")


if __name__ == "__main__":
    main()
