"""Email notification service — closer alerts for high-intent prospects.

Sends an email to configured closer addresses when a prospect shows a strong
purchase signal (conversion_intent_detected, offer_interest_detected, or
any needs_human=True message with haute priority).

Configuration (Coolify env vars):
    CLOSER_NOTIFICATION_EMAIL  — comma-separated recipient list
    SMTP_HOST                  — e.g. smtp.gmail.com
    SMTP_PORT                  — default 587 (STARTTLS)
    SMTP_USER                  — sender login
    SMTP_PASSWORD              — sender password
    SMTP_FROM                  — sender address

If SMTP is not configured, the notification is logged as a warning only
(graceful degradation — never breaks the main request flow).
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

# Intents that should trigger a closer notification
HIGH_INTENT_INTENTS = {
    "conversion_intent_detected",
    "offer_interest_detected",
    "payment_failure_followup_needed",
    "installment_plan_request",
    "human_escalation",
}


def should_notify_closer(intent: str, needs_human: bool) -> bool:
    """Return True if this message warrants a closer notification."""
    return intent in HIGH_INTENT_INTENTS or needs_human


def notify_closer(
    phone: str,
    contact_id: str | None,
    message_text: str,
    ai_reply: str,
    intent: str,
    score: int = 0,
) -> bool:
    """Send a closer notification email.

    Returns True if the email was sent, False otherwise (SMTP not configured,
    no recipients, or send failure — all fail silently).
    """
    from shared.config.settings import settings

    recipients_raw = settings.closer_notification_email.strip()
    if not recipients_raw:
        logger.debug("Closer notification skipped — CLOSER_NOTIFICATION_EMAIL not set")
        return False

    if not settings.smtp_host:
        logger.warning(
            "Closer alert (SMTP not configured): phone=%s intent=%s message=%r",
            phone, intent, message_text[:120],
        )
        return False

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        return False

    subject = f"🔥 Prospect chaud — {intent} | {phone}"
    body = f"""Un prospect a déclenché une alerte haute priorité sur WhatsApp.

━━━ Profil contact ━━━
Téléphone   : {phone}
Contact ID  : {contact_id or "inconnu"}
Score actuel: {score} pts
Intent      : {intent}

━━━ Message reçu ━━━
{message_text}

━━━ Réponse IA envoyée ━━━
{ai_reply}

━━━ Action recommandée ━━━
Contacter ce prospect dans les prochaines minutes via WhatsApp ou appel.

---
Plateforme WhatsApp Challenge Amazon FBA
"""

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

        logger.info(
            "Closer notification sent: phone=%s intent=%s recipients=%s",
            phone, intent, recipients,
        )
        return True

    except Exception as exc:
        logger.error("Closer notification failed: %s", exc)
        return False
