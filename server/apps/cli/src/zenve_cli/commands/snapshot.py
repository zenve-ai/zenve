from __future__ import annotations

import re
import subprocess
from pathlib import Path

import typer

from zenve_cli.core.config import load_project_settings
from zenve_cli.core.env import new_run_id, resolve_github_token
from zenve_cli.integrations.github.client import GitHubClient
from zenve_cli.integrations.github.snapshot import build_snapshot, write_snapshot


def repo_slug_from_url(url: str) -> str | None:
    """Extract `owner/repo` from an HTTPS or SSH GitHub URL."""
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


def git_remote_slug(repo_root: Path) -> str | None:
    """Return the `owner/repo` slug from git remote origin."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
        )
        return repo_slug_from_url(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def cmd(repo_root: Path = Path(".")) -> None:
    """Fetch current GitHub state and write it to `.zenve/snapshot.json`."""
    token = resolve_github_token()
    if not token:
        typer.echo("✗ No GitHub token found. Run `gh auth login`.")
        raise typer.Exit(1)

    load_project_settings(repo_root)

    repo = git_remote_slug(repo_root)
    if not repo:
        typer.echo("✗ Could not determine repo. Ensure git remote origin is a GitHub URL.")
        raise typer.Exit(1)

    run_id = new_run_id()

    with GitHubClient(token, repo) as gh:
        snapshot = build_snapshot(gh, run_id)

    path = write_snapshot(repo_root, snapshot)
    typer.echo(f"✓ snapshot written to {path}")
    typer.echo(f"  issues: {len(snapshot.issues)}")
    typer.echo(f"  pull_requests: {len(snapshot.pull_requests)}")
    typer.echo(f"  branches: {len(snapshot.branches)}")
