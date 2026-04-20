from __future__ import annotations

import json
from pathlib import Path

import typer

from zenve_cli.core.config import zenve_dir
from zenve_cli.core.discovery import AGENTS_SUBDIR, discover_agents
from zenve_cli.models.settings import AgentSettings

agent_app = typer.Typer(help="Agent management commands")


def iter_agent_dirs(repo_root: Path) -> list[Path]:
    adir = zenve_dir(repo_root) / AGENTS_SUBDIR
    if not adir.exists():
        return []
    return sorted(d for d in adir.iterdir() if d.is_dir() and not d.name.startswith("."))


def load_agent_settings(path: Path) -> AgentSettings | None:
    settings_path = path / "settings.json"
    if not settings_path.exists():
        return None
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    return AgentSettings.model_validate(raw)


def save_agent_settings(path: Path, settings: AgentSettings) -> None:
    settings_path = path / "settings.json"
    settings_path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")


@agent_app.command("list")
def list_agents(repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """List all agents and their enabled/disabled status."""
    dirs = iter_agent_dirs(repo_root)
    if not dirs:
        typer.echo("No agents found.")
        return
    for d in dirs:
        s = load_agent_settings(d)
        if s is None:
            typer.echo(f"  {d.name:<20} (missing settings.json)")
            continue
        status = "enabled" if s.enabled else "disabled"
        typer.echo(f"  {s.name:<20} {status:<10} {s.github_label:<20} picks_up={s.picks_up}")


@agent_app.command("logs")
def logs(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Show run history for a specific agent."""
    agent_dir = zenve_dir(repo_root) / AGENTS_SUBDIR / name
    runs_dir = agent_dir / "runs"
    if not runs_dir.exists():
        typer.echo(f"No runs for agent {name!r}.")
        return
    files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        typer.echo(f"No runs for agent {name!r}.")
        return
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        typer.echo(
            f"  {data.get('run_id', '?'):<24} {data.get('status', '?'):<10} "
            f"{data.get('finished_at', '?')}"
        )


@agent_app.command("enable")
def enable(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Enable a disabled agent."""
    set_enabled(repo_root, name, True)
    typer.echo(f"✓ Enabled agent {name!r}")


@agent_app.command("disable")
def disable(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Disable an agent without removing it."""
    set_enabled(repo_root, name, False)
    typer.echo(f"✓ Disabled agent {name!r}")


def set_enabled(repo_root: Path, name: str, enabled: bool) -> None:
    agents = discover_agents(repo_root)
    path: Path | None = None
    for a in agents:
        if a.name == name:
            path = a.path
            break
    if path is None:
        path = zenve_dir(repo_root) / AGENTS_SUBDIR / name
        if not (path / "settings.json").exists():
            typer.echo(f"✗ Agent not found: {name!r}")
            raise typer.Exit(1)

    settings = load_agent_settings(path)
    if settings is None:
        typer.echo(f"✗ Could not load settings for {name!r}")
        raise typer.Exit(1)
    updated = settings.model_copy(update={"enabled": enabled})
    save_agent_settings(path, updated)
