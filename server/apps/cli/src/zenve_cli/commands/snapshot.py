from __future__ import annotations

import re
from pathlib import Path

import typer

from zenve_cli.core.config import load_project_settings
from zenve_cli.core.env import EnvError, load_env
from zenve_cli.github.client import GitHubClient
from zenve_cli.github.snapshot import build_snapshot, write_snapshot


def repo_slug_from_url(url: str) -> str | None:
    """Extract `owner/repo` from an HTTPS or SSH GitHub URL."""
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


def cmd(repo_root: Path = Path(".")) -> None:
    """Fetch current GitHub state and write it to `.zenve/snapshot.json`."""
    try:
        env = load_env()
    except EnvError as exc:
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc

    settings = load_project_settings(repo_root)

    repo = settings.repo or repo_slug_from_url(env.repo_url)
    if not repo:
        typer.echo("✗ Could not determine repo (check settings.repo or ZENVE_REPO_URL).")
        raise typer.Exit(1)

    with GitHubClient(env.github_token, repo) as gh:
        snapshot = build_snapshot(gh, env.run_id)

    path = write_snapshot(repo_root, snapshot)
    typer.echo(f"✓ snapshot written to {path}")
    typer.echo(f"  issues: {len(snapshot.issues)}")
    typer.echo(f"  pull_requests: {len(snapshot.pull_requests)}")
    typer.echo(f"  branches: {len(snapshot.branches)}")
