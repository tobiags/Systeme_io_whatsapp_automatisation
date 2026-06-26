import logging as _logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "whatsapp-engagement-platform"
    environment: str = "local"
    postgres_dsn: str = "postgresql+psycopg://platform:changeme@platform-db:5432/platform"
    redis_url: str = "redis://redis:6379/0"
    wati_api_url: str = ""
    wati_api_token: str = ""
    wati_channel_phone_number: str = ""
    openai_api_key: str = ""
    whatsapp_auto_reply_enabled: bool = False
    # Admin API key — all non-public endpoints require X-API-Key: <value>.
    # Leave empty to disable auth (local dev / tests).
    platform_api_key: str = ""
    # Token used by the lightweight operator portal for manual StreamYard sync.
    ops_portal_token: str = ""

    # ── Closer / transfer ────────────────────────────────────────────────────
    # Email of the closer's Wati account — conversation is auto-assigned when
    # needs_human=True.  Must match the email used to log into Wati.
    # Can be overridden per-edition from the admin console.
    wati_closer_email: str = ""

    # ── Closer notifications ──────────────────────────────────────────────────
    # Comma-separated list of email addresses to notify when a high-intent
    # prospect is detected (conversion_intent_detected or needs_human + haute).
    # Uses SMTP if smtp_host is set, otherwise logs a warning.
    closer_notification_email: str = ""   # e.g. "closer1@team.com,closer2@team.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@ecommercecentrale.com"

    # ── Commercial URLs ───────────────────────────────────────────────────────
    # Payment / programme join link (sent H+2 into Day 3 live).
    # ⚠️ To be provided by client — set in Coolify env vars.
    program_payment_url: str = ""

    # Systeme.io REST API key (for proactive contact sync by tag).
    # Set in Coolify env: SYSTEMEIO_API_KEY=<your key>
    systemeio_api_key: str = ""

    # OnceHub qualification form for post-challenge closer booking.
    oncehub_form_url: str = "https://www.ecommercecentrale.com/formulaire-challenge"
    # OnceHub webhook secret — used to verify the X-OnceHub-Signature header.
    # Set in Coolify env: ONCEHUB_WEBHOOK_SECRET=<value from OnceHub>
    oncehub_webhook_secret: str = ""

    # Replay URLs shared after the challenge.
    replay_day1_url: str = ""
    replay_day2_url: str = ""
    replay_day3_url: str = ""

    @model_validator(mode="after")
    def _check_wati_credentials(self) -> "Settings":
        if bool(self.wati_api_url) != bool(self.wati_api_token):
            _logging.getLogger(__name__).warning(
                "Wati credentials partially set (url=%s, token=%s) — "
                "falling back to MockProvider. Set both WATI_API_URL and WATI_API_TOKEN.",
                bool(self.wati_api_url),
                bool(self.wati_api_token),
            )
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
