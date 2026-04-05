from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Secret key for signing JWT tokens
    secret_key: str

    # SQLite database file path (fallback)
    sqlite_database_url: str = "zenve.db"

    # Full PostgreSQL connection string
    pg_database_url: str | None = None

    # Base directory for org/agent data on disk
    data_dir: str = "/data"

    # Optional token to protect the org bootstrap endpoint
    setup_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
