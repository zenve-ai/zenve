from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass


class EnvError(RuntimeError):
    """Raised when required environment variables are missing."""


@dataclass(frozen=True)
class Env:
    github_token: str
    run_id: str
    webhook_url: str | None
    webhook_secret: str | None


def resolve_github_token() -> str | None:
    """Return a GitHub token from `gh auth token`."""
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


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def load_env() -> Env:
    token = resolve_github_token()
    if not token:
        raise EnvError("No GitHub token. Run `gh auth login`.")
    return Env(
        github_token=token,
        run_id=new_run_id(),
        webhook_url=os.environ.get("ZENVE_WEBHOOK_URL") or None,
        webhook_secret=os.environ.get("ZENVE_WEBHOOK_SECRET") or None,
    )
