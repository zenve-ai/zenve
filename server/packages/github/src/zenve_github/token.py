from __future__ import annotations

import os
import subprocess


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
