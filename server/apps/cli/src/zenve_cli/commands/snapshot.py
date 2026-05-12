from __future__ import annotations

import re
import subprocess
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_cli.runtime.client import ensure_runtime, report_error, resolve_workspace_id, runtime_request

console = Console()


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
    ensure_runtime()
    workspace_id = resolve_workspace_id(repo_root)
    resp = runtime_request("POST", f"/api/v1/workspaces/{workspace_id}/snapshot", timeout=60.0)
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    data = resp.json()
    path = repo_root.expanduser().resolve() / ".zenve" / "snapshot.json"

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("RESOURCE", style="cyan", no_wrap=True)
    table.add_column("COUNT", justify="right")

    table.add_row("Issues", str(data["issues_count"]))
    table.add_row("Pull requests", str(data["pull_requests_count"]))
    table.add_row("Branches", str(data["branches_count"]))

    console.print()
    console.print(f"[green]✓[/green] Snapshot written to [dim]{path}[/dim]")
    console.print()
    console.print(table)
    console.print()
