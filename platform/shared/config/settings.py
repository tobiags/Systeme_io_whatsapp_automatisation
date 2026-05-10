from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "whatsapp-engagement-platform"
    environment: str = "local"
    postgres_dsn: str = "postgresql+psycopg://platform:changeme@platform-db:5432/platform"
    redis_url: str = "redis://redis:6379/0"
    wati_api_url: str = ""
    wati_api_token: str = ""
    openai_api_key: str = ""
    # Admin API key — all non-public endpoints require X-API-Key: <value>.
    # Leave empty to disable auth (local dev / tests).
    platform_api_key: str = ""

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

    # OnceHub qualification form for post-challenge closer booking.
    oncehub_form_url: str = "https://www.ecommercecentrale.com/formulaire-challenge"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
