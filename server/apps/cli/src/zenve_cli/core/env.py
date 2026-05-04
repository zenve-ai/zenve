from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass

from dotenv import load_dotenv


class EnvError(RuntimeError):
    """Raised when required environment variables are missing."""


@dataclass(frozen=True)
class Env:
    github_token: str
    run_id: str
    webhook_url: str | None
    webhook_secret: str | None


def resolve_github_token() -> str | None:
    """Return a GitHub token — ZENVE_GH_TOKEN env var, then `gh auth token`."""
    if token := os.environ.get("ZENVE_GH_TOKEN"):
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def resolve_agent_github_token(agent_slug: str, default_token: str) -> str:
    """Return the GitHub token for a specific agent.

    Priority:
    1. ZENVE_GH_{SLUG} (e.g. ZENVE_GH_CODE_REVIEW for slug code-review)
    2. default_token (global ZENVE_GH_TOKEN or gh auth token)
    """
    env_key = "ZENVE_GH_" + agent_slug.upper().replace("-", "_")
    return os.environ.get(env_key) or default_token


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def load_env(repo_root: "Path | None" = None) -> Env:
    from pathlib import Path

    load_dotenv(dotenv_path=Path(repo_root or ".") / ".env")
    token = resolve_github_token()
    if not token:
        raise EnvError("No GitHub token. Run `gh auth login`.")
    return Env(
        github_token=token,
        run_id=new_run_id(),
        webhook_url=os.environ.get("ZENVE_WEBHOOK_URL") or None,
        webhook_secret=os.environ.get("ZENVE_WEBHOOK_SECRET") or None,
    )
