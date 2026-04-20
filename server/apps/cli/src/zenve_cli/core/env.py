from __future__ import annotations

import os
from dataclasses import dataclass

REQUIRED_VARS = (
    "GITHUB_TOKEN",
    "ZENVE_RUN_ID",
    "ZENVE_REPO_URL",
    "ANTHROPIC_API_KEY",
)


class EnvError(RuntimeError):
    """Raised when required environment variables are missing."""


@dataclass(frozen=True)
class Env:
    github_token: str
    run_id: str
    repo_url: str
    anthropic_api_key: str
    webhook_url: str | None
    webhook_secret: str | None


def load_env() -> Env:
    missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        raise EnvError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return Env(
        github_token=os.environ["GITHUB_TOKEN"],
        run_id=os.environ["ZENVE_RUN_ID"],
        repo_url=os.environ["ZENVE_REPO_URL"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        webhook_url=os.environ.get("ZENVE_WEBHOOK_URL") or None,
        webhook_secret=os.environ.get("ZENVE_WEBHOOK_SECRET") or None,
    )
