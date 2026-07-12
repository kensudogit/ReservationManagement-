from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://srm:srm_secret@localhost:5432/srm"
    secret_key: str = "dev-secret-key-change-me"
    access_token_expire_minutes: int = 1440
    cancel_hours_before: int = 24
    cors_origins: str = "http://localhost:3000,http://localhost:3020"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/google/callback"
    frontend_url: str = "http://localhost:3000"
    algorithm: str = "HS256"

    @field_validator("database_url", mode="before")
    @classmethod
    def _db_url(cls, value: str) -> str:
        return normalize_database_url(value or "")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
