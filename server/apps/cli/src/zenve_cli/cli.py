from __future__ import annotations

from pathlib import Path

import typer

from zenve_cli.commands import init as init_cmd
from zenve_cli.commands import pipeline as pipeline_cmd
from zenve_cli.commands import snapshot as snapshot_cmd
from zenve_cli.commands import start as start_cmd
from zenve_cli.commands import status as status_cmd
from zenve_cli.commands.agent import agent_app

app = typer.Typer(name="zenve", help="Zenve CLI — autonomous agents in your repo")
app.add_typer(agent_app, name="agent")


@app.command()
def init(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
    description: str | None = typer.Option(None, "--description", help="Project description"),
) -> None:
    """Scaffold .zenve/ folder interactively."""
    init_cmd.cmd(repo_root=repo, description=description)


@app.command()
def start(
    agent: str | None = typer.Option(None, "--agent", help="Run only this agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan, no writes"),
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Run all enabled agents against a fresh GitHub snapshot."""
    start_cmd.cmd(repo_root=repo, agent=agent, dry_run=dry_run)


@app.command()
def snapshot(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Fetch GitHub state and write `.zenve/snapshot.json`."""
    snapshot_cmd.cmd(repo_root=repo)


@app.command()
def pipeline(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Display and validate the pipeline from `.zenve/settings.json`."""
    pipeline_cmd.cmd(repo_root=repo)


@app.command()
def status(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Show last run result per agent."""
    status_cmd.cmd(repo_root=repo)
