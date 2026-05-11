from __future__ import annotations

import json
from pathlib import Path

import httpx
import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_engine.config import ConfigError, zenve_dir
from zenve_engine.discovery import DiscoveryError, discover_agents

from zenve_cli.runtime.client import ensure_runtime, runtime_url

console = Console()


def latest_run(agent_path: Path) -> dict | None:
    runs_dir = agent_path / "runs"
    if not runs_dir.exists():
        return None
    files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def fetch_active_run(workspace_id: str) -> dict | None:
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{runtime_url()}/api/v1/workspaces/{workspace_id}/runs/active-run")
        if resp.status_code == 200:
            return resp.json()
    except httpx.ConnectError:
        pass
    return None


def fetch_workspace_id(repo_root: Path) -> str | None:
    abs_path = str(repo_root.expanduser().resolve())
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{runtime_url()}/api/v1/workspaces")
        if resp.status_code == 200:
            for w in resp.json():
                if w["path"] == abs_path:
                    return w["id"]
    except httpx.ConnectError:
        pass
    return None


def cmd(repo_root: Path = Path(".")) -> None:
    """Show last run result per agent."""
    ensure_runtime()
    if not zenve_dir(repo_root).exists():
        typer.echo(f"✗ No `.zenve/` folder at {repo_root}")
        raise typer.Exit(1)

    try:
        agents = discover_agents(repo_root)
    except (ConfigError, DiscoveryError) as exc:
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc

    if not agents:
        typer.echo("No enabled agents found.")
        return

    # ── Active run (best-effort, runtime may not be running) ─────────────────
    workspace_id = fetch_workspace_id(repo_root)
    active_run = fetch_active_run(workspace_id) if workspace_id else None

    console.print()

    if active_run:
        banner = Text()
        banner.append("  ● ", style="bold cyan")
        banner.append("active run  ", style="bold")
        banner.append(active_run["run_id"][:12], style="cyan")
        banner.append(f"  {active_run['status']}", style="dim")
        console.print(banner)
        console.print()

    # ── Agent table ───────────────────────────────────────────────────────────
    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("AGENT", style="cyan", no_wrap=True)
    table.add_column("STATUS", justify="center")
    table.add_column("RUN ID", style="dim")
    table.add_column("STARTED", style="dim")

    for agent in agents:
        run = latest_run(agent.path)
        if run is None:
            table.add_row(agent.name, Text("—", style="dim"), "—", "—")
            continue
        status = run.get("status", "?")
        if status == "done":
            status_text = Text("● done", style="green")
        elif status == "failed":
            status_text = Text("✗ failed", style="red")
        else:
            status_text = Text(status, style="dim")
        run_id = run.get("run_id", "?")[:12]
        started = run.get("started_at", "?").replace("T", " ").replace("Z", "")
        table.add_row(agent.name, status_text, run_id, started)

    console.print(table)
    console.print()
