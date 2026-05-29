"""Wati API client — send session messages (24h customer care window)."""
import httpx

from bot.app.config import get_settings


def _normalise_phone(phone: str) -> str:
    p = phone.strip()
    if p.startswith("+"):
        p = p[1:]
    elif p.startswith("00"):
        p = p[2:]
    return p


def send_session_message(phone: str, text: str) -> dict:
    """Send a free-text reply inside the active 24h WhatsApp customer care window.

    Returns {"status": "sent"} on success, {"status": "failed", "error": ...} on failure.
    Wati V1 endpoint: POST {api_url}/api/v1/sendSessionMessage/{phone}?messageText=...
    """
    settings = get_settings()
    if not settings.wati_api_url or not settings.wati_api_token:
        return {"status": "skipped", "reason": "wati_not_configured"}

    phone_clean = _normalise_phone(phone)
    payload: dict = {}
    if settings.wati_channel_phone_number:
        payload["channelPhoneNumber"] = settings.wati_channel_phone_number

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{settings.wati_api_url.rstrip('/')}/api/v1/sendSessionMessage/{phone_clean}",
                params={"messageText": text},
                json=payload or None,
                headers={
                    "Authorization": f"Bearer {settings.wati_api_token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            if data.get("result") is False:
                return {
                    "status": "failed",
                    "error": data.get("message") or data.get("info") or "Wati rejected message",
                }
            return {"status": "sent", "provider_id": data.get("id") or data.get("messageId")}
    except httpx.HTTPError as exc:
        return {"status": "failed", "error": str(exc)}
