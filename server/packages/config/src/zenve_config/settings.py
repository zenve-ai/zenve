from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Secret key for signing JWT tokens
    secret_key: str = "dev-secret-key-change-in-production"

    # SQLite database file path (fallback)
    sqlite_database_url: str = "zenve.db"

    # Full PostgreSQL connection string
    pg_database_url: str | None = None

    # Base directory for agent data on disk
    data_dir: str = "/data"

    # Directory containing Jinja2 template sets (e.g. default/)
    templates_dir: str = "/data/templates"

    # GitHub App credentials
    github_app_id: int | None = None
    github_app_private_key: str | None = None  # PEM string or path to .pem file
    github_webhook_secret: str | None = None
    zenve_webhook_secret: str | None = None

    # GitHub OAuth App credentials (user login flow)
    github_app_client_id: str | None = None
    github_app_client_secret: str | None = None
    github_frontend_redirect_uri: str | None = None

    # GitHub public repo for agent templates (e.g. "myorg/agent-templates")
    github_agents_repo: str | None = None
    # Optional PAT for higher GitHub API rate limits
    github_token: str | None = None

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), env_file_encoding="utf-8", extra="ignore")

    @property
    def github_private_key(self) -> str | None:
        """Return the PEM key, reading from file if the value is a .pem path."""
        val = self.github_app_private_key
        if not val:
            return None
        if val.strip().endswith(".pem") and Path(val.strip()).exists():
            return Path(val.strip()).read_text()
        return val


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
