from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from zenve_cli import __version__

from zenve_cli.commands import doctor as doctor_cmd
from zenve_cli.commands import env as env_cmd
from zenve_cli.commands import init as init_cmd
from zenve_cli.commands import pipeline as pipeline_cmd
from zenve_cli.commands import run as run_cmd
from zenve_cli.commands import snapshot as snapshot_cmd
from zenve_cli.commands import status as status_cmd
from zenve_cli.commands.agent import agent_app
from zenve_cli.commands.skill import skill_app
from zenve_cli.console import print_logo

app = typer.Typer(name="zenve", help="Zenve CLI — autonomous agents in your repo")
app.add_typer(agent_app, name="agents")
app.add_typer(skill_app, name="skills")


def version_callback(value: bool) -> None:
    if value:
        print_logo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True, help="Show version and exit")] = None,
) -> None:
    if ctx.invoked_subcommand is not None and ctx.invoked_subcommand != "run":
        print_logo()


@app.command()
def env(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Show resolved environment variables and effective GitHub token."""
    env_cmd.cmd(repo_root=repo)


@app.command()
def doctor(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Check that this repo is correctly set up for Zenve."""
    doctor_cmd.cmd(repo_root=repo)


@app.command()
def init(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
    description: str | None = typer.Option(None, "--description", help="Project description"),
) -> None:
    """Scaffold .zenve/ folder interactively."""
    init_cmd.cmd(repo_root=repo, description=description)


@app.command()
def run(
    agent: str | None = typer.Option(None, "--agent", help="Run only this agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan, no writes"),
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Run all enabled agents against a fresh GitHub snapshot."""
    run_cmd.cmd(repo_root=repo, agent=agent, dry_run=dry_run)


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
