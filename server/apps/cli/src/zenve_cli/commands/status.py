from __future__ import annotations

import json
from pathlib import Path

import typer

from zenve_cli.core.config import ConfigError, zenve_dir
from zenve_cli.core.discovery import DiscoveryError, discover_agents


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


def cmd(repo_root: Path = Path(".")) -> None:
    """Show last run result per agent."""
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

    for agent in agents:
        run = latest_run(agent.path)
        if run is None:
            typer.echo(f"  {agent.name:<20} (no runs)")
            continue
        status = run.get("status", "?")
        run_id = run.get("run_id", "?")
        typer.echo(f"  {agent.name:<20} {status:<10} {run_id}")
