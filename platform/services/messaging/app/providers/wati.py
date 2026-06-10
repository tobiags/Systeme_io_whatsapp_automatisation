import logging
import time

import httpx

from shared.config.settings import settings
from services.messaging.app.providers.base import MessagingProvider

logger = logging.getLogger(__name__)

# Wati rejects bursts with 400/429 — observed 2026-06-10: 304/607 template sends
# failed when fired back-to-back with no delay.  Throttle every send and retry
# transient rejections with backoff.
_SEND_MIN_INTERVAL = 0.5   # seconds between consecutive sends (≈2 req/s)
_SEND_MAX_ATTEMPTS = 3     # 1 initial + 2 retries
_RETRY_BACKOFF = 2.0       # seconds, doubled each retry (2s, 4s)

_last_send_at = 0.0


def _throttle() -> None:
    """Global pacing: ensure at least _SEND_MIN_INTERVAL between Wati requests."""
    global _last_send_at
    wait = _SEND_MIN_INTERVAL - (time.monotonic() - _last_send_at)
    if wait > 0:
        time.sleep(wait)
    _last_send_at = time.monotonic()


class WatiProvider(MessagingProvider):
    """
    Send WhatsApp template messages via Wati API v2.

    WATI_API_URL format (from Context7 / Wati docs):
        https://live-mt-server.wati.io/{tenant_id}
    The tenant_id is part of the base URL — NOT a separate setting.

    Endpoint used (V2, recommended):
        POST {api_url}/api/v2/sendTemplateMessage?whatsappNumber={phone}

    Auth: Bearer token in Authorization header.
    Phone format: international without '+' (e.g. 33600000001, not +33600000001).
    """

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token

    @staticmethod
    def _normalise_phone(phone: str) -> str:
        """Normalize to digits-only international format — Wati rejects '+' or '00' prefixes.

        +33612345678  → 33612345678
        0033612345678 → 33612345678
        33612345678   → 33612345678  (already clean)
        """
        p = phone.strip()
        if p.startswith("+"):
            p = p[1:]
        elif p.startswith("00"):
            p = p[2:]
        return p

    def send_template(self, contact_id: str, template_key: str, variables: dict[str, str]) -> dict:
        """
        Send a single template message to one recipient.

        Args:
            contact_id: WhatsApp number (with or without leading '+').
            template_key: Wati template name (must be pre-approved in Wati).
            variables: Template parameters as {name: value} mapping.
        """
        phone = self._normalise_phone(contact_id)
        parameters = [{"name": k, "value": v} for k, v in variables.items()]

        payload = {
            "template_name": template_key,
            "broadcast_name": f"{template_key}_{phone}",
            "parameters": parameters,
        }
        if settings.wati_channel_phone_number:
            payload["channelNumber"] = settings.wati_channel_phone_number

        last_error = "Wati template send failed"
        for attempt in range(_SEND_MAX_ATTEMPTS):
            if attempt > 0:
                time.sleep(_RETRY_BACKOFF * (2 ** (attempt - 1)))
                logger.info("Wati retry %d/%d for %s", attempt, _SEND_MAX_ATTEMPTS - 1, phone)
            _throttle()
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{self.api_url}/api/v2/sendTemplateMessage",
                        params={"whatsappNumber": phone},
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_token}",
                            "Content-Type": "application/json",
                        },
                    )
                    if resp.status_code in (400, 429) or resp.status_code >= 500:
                        # 400 can be rate-limiting in disguise (observed 2026-06-10):
                        # the same number succeeds on retry. Keep the body for diagnosis.
                        last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("result") is False:
                        return {
                            "provider": "wati",
                            "provider_message_id": f"wati_{phone}",
                            "status": "failed",
                            "template_key": template_key,
                            "error": data.get("message") or data.get("info") or data.get("error") or "Wati template send failed",
                        }
                    # V2 response: {"result": true, "templateName": "...", "receivers": [...]}
                    receivers = data.get("receivers", [])
                    provider_id = receivers[0].get("localMessageId", f"wati_{phone}") if receivers else f"wati_{phone}"
                    return {
                        "provider": "wati",
                        "provider_message_id": provider_id,
                        "status": "queued",
                        "template_key": template_key,
                    }
            except httpx.HTTPError as exc:
                last_error = str(exc)
                continue

        return {
            "provider": "wati",
            "provider_message_id": f"wati_{phone}",
            "status": "failed",
            "template_key": template_key,
            "error": last_error,
        }

    def send_text(self, contact_id: str, text: str) -> dict:
        """Send a free-form reply inside the active 24h customer care window.

        Official Wati reference:
          POST {api_url}/api/v1/sendSessionMessage/{whatsappNumber}?messageText=...
        """
        phone = self._normalise_phone(contact_id)

        try:
            with httpx.Client(timeout=10.0) as client:
                payload = {}
                if settings.wati_channel_phone_number:
                    payload["channelPhoneNumber"] = settings.wati_channel_phone_number
                resp = client.post(
                    f"{self.api_url}/api/v1/sendSessionMessage/{phone}",
                    params={"messageText": text},
                    json=payload or None,
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json() if resp.content else {}
                if data.get("result") is False:
                    return {
                        "provider": "wati",
                        "provider_message_id": f"wati_session_{phone}",
                        "status": "failed",
                        "text": text,
                        "error": data.get("message") or data.get("info") or data.get("error") or "Wati session send failed",
                    }
                provider_id = (
                    data.get("id")
                    or data.get("messageId")
                    or data.get("localMessageId")
                    or f"wati_session_{phone}"
                )
                return {
                    "provider": "wati",
                    "provider_message_id": provider_id,
                    "status": "queued",
                    "text": text,
                }
        except httpx.HTTPError as exc:
            return {
                "provider": "wati",
                "provider_message_id": f"wati_session_{phone}",
                "status": "failed",
                "text": text,
                "error": str(exc),
            }
