from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (shared with platform)
    postgres_dsn: str = "postgresql://platform:platform@localhost:5432/platform"

    # Wati
    wati_api_url: str = ""
    wati_api_token: str = ""
    wati_channel_phone_number: str = ""

    # Anthropic Claude (primary AI engine)
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"

    # Security
    bot_api_key: str = ""          # X-Bot-Key header for admin endpoints
    wati_webhook_secret: str = ""  # optional HMAC validation

    # Behaviour
    auto_reply_enabled: bool = True
    max_history_messages: int = 10  # conversation turns to feed Claude
    dedup_window_seconds: int = 60  # ignore duplicate text within this window

    # Notifications
    closer_email: str = ""         # comma-separated, receives escalation alerts
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "bot@yourdomain.com"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
