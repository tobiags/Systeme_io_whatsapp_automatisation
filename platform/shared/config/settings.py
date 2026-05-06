from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "whatsapp-engagement-platform"
    environment: str = "local"
    postgres_dsn: str = "postgresql+psycopg://platform:changeme@platform-db:5432/platform"
    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
