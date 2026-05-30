from __future__ import annotations

import asyncio
import dataclasses
import json
import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_adapters import build_default_registry
from zenve_cli.commands.snapshot import git_remote_slug
from zenve_cli.console import ZenveTUI
from zenve_cli.runtime.client import (
    ensure_runtime,
    report_error,
    resolve_workspace_id,
    runtime_request,
    runtime_url,
)
from zenve_engine.config import ConfigError, load_workspace_settings
from zenve_engine.discovery import DiscoveryError, discover_agents
from zenve_engine.env import EnvError, load_env
from zenve_engine.events import types as et
from zenve_engine.events.emitter import EventEmitter
from zenve_engine.exec.executor import DryRunResult
from zenve_engine.git.commit import (
    GitError,
    commit_zenve_dir,
    fetch_origin,
    has_dirty_outside_zenve,
    has_dirty_zenve,
    remote_branch_exists,
)
from zenve_engine.github.client import GitHubClient
from zenve_engine.github.snapshot import build_snapshot, write_snapshot

run_app = typer.Typer(help="Run agents and inspect run history", invoke_without_command=True)
console = Console()


@run_app.callback()
def run_callback(
    ctx: typer.Context,
    agent: str | None = typer.Option(None, "--agent", help="Run only this agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan, no writes"),
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Run all enabled agents against a fresh GitHub snapshot."""
    if ctx.invoked_subcommand is None:
        execute(agent=agent, dry_run=dry_run, repo=repo)




def execute_dry(agent: str | None, repo_root: Path) -> None:
    """Run agents in dry-run mode locally — shows plan without writes."""
    from zenve_engine.exec.parallel import run_all

    status = console.status("[cyan]starting zenve…[/cyan]", spinner="dots")
    status.start()
    try:
        status.update("[cyan]loading env & config…[/cyan]")
        env = load_env(repo_root)
        workspace = load_workspace_settings(repo_root)
        status.update("[cyan]discovering agents…[/cyan]")
        agents = discover_agents(repo_root, only=agent)
    except EnvError as exc:
        status.stop()
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc
    except (ConfigError, DiscoveryError) as exc:
        status.stop()
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc

    if not agents:
        status.stop()
        typer.echo("No enabled agents to run.")
        raise typer.Exit(0)

    status.update("[cyan]checking git remote…[/cyan]")
    repo_slug = git_remote_slug(repo_root)
    if not repo_slug:
        status.stop()
        typer.echo("✗ Could not determine repo. Ensure git remote origin is a GitHub URL.")
        raise typer.Exit(1)

    if has_dirty_outside_zenve(repo_root):
        status.stop()
        typer.echo("✗ Local repo has uncommitted changes outside .zenve/.")
        typer.echo(
            "  Zenve cannot run safely because generated worktrees/snapshots may be based on stale or mixed state."
        )
        typer.echo("")
        typer.echo("  Commit, stash, or discard your changes, then run again.")
        raise typer.Exit(1)

    if has_dirty_zenve(repo_root):
        status.stop()
        if not typer.confirm(
            "Local .zenve/ has uncommitted changes. Commit and push them before running?",
            default=True,
        ):
            typer.echo("✗ Aborted. Commit, stash, or discard your .zenve/ changes, then run again.")
            raise typer.Exit(1)
        status.start()
        status.update("[cyan]committing .zenve/ changes…[/cyan]")
        try:
            commit_zenve_dir(
                repo_root,
                f"{workspace.commit_message_prefix} update .zenve config",
                branch=workspace.default_branch,
            )
        except GitError as exc:
            status.stop()
            typer.echo(f"✗ Failed to commit .zenve/ changes: {exc}")
            raise typer.Exit(1) from exc

    status.update("[cyan]fetching origin…[/cyan]")
    try:
        fetch_origin(repo_root)
    except GitError as exc:
        status.stop()
        typer.echo(f"✗ git fetch origin failed: {exc}")
        raise typer.Exit(1) from exc

    if not remote_branch_exists(repo_root, workspace.default_branch):
        status.stop()
        typer.echo(f"✗ Remote branch origin/{workspace.default_branch} not found after fetch.")
        raise typer.Exit(1)

    status.stop()

    env_vars = {"ZENVE_RUN_ID": env.run_id, "GH_TOKEN": env.github_token}

    emitter = EventEmitter(
        repo_root=repo_root,
        run_id=env.run_id,
        webhook_url=env.webhook_url,
        webhook_secret=env.webhook_secret,
        on_event=None,
    )
    emitter.emit(
        et.RUN_STARTED,
        data={"agents": [a.name for a in agents], "repo": repo_slug, "dry_run": True},
    )

    with GitHubClient(env.github_token, repo_slug) as gh:
        snapshot = build_snapshot(gh, env.run_id)
        write_snapshot(repo_root, snapshot)
        emitter.emit(
            et.SNAPSHOT_FETCHED,
            data={
                "issues": len(snapshot.issues),
                "pull_requests": len(snapshot.pull_requests),
                "branches": len(snapshot.branches),
            },
        )

        registry = build_default_registry()
        results = asyncio.run(
            run_all(
                agents=agents,
                snapshot=snapshot,
                workspace=workspace,
                repo_root=repo_root,
                run_id=env.run_id,
                registry=registry,
                gh=gh,
                emitter=emitter,
                env_vars=env_vars,
                dry_run=True,
            )
        )

    dry_lookup = {r.agent_name: r for r in results if isinstance(r, DryRunResult)}
    label_w = 12

    def row(label: str, value: str, value_style: str = "default") -> None:
        line = Text()
        line.append(f"    {label:<{label_w}}", style="dim")
        line.append(value, style=value_style)
        console.print(line)

    console.print()
    for ag in agents:
        slug_line = Text()
        slug_line.append("  ◆ ", style="bold cyan")
        slug_line.append(ag.name, style="bold")
        console.print(slug_line)

        dr = dry_lookup.get(ag.name)
        if dr is None:
            console.print("    [dim]no result[/dim]")
            console.print()
            continue

        row("name", ag.settings.name)
        row("label", dr.label, "cyan")
        row("model", str(ag.settings.adapter_config.get("model", "")), "dim")

        if dr.item is not None:
            pick_text = f"{dr.item.kind} #{dr.item.number}: {dr.item.title}"
            row("would pick", pick_text)

            ctx_dict = {k: v for k, v in dataclasses.asdict(dr.context).items() if not callable(v)}
            ctx_json = json.dumps(ctx_dict, indent=2)
            indented = "\n".join(f"    {line}" for line in ctx_json.splitlines())
            console.print()
            console.print("    context", style="dim")
            console.print(indented, style="dim")
        else:
            row("would pick", "nothing to do", "dim")

        console.print()

    emitter.emit(et.RUN_COMPLETED, data={"dry_run": True})


def stream_run_events(workspace_id: str, run_id: str) -> Iterator[dict]:
    url = f"{runtime_url()}/api/v1/workspaces/{workspace_id}/runs/{run_id}/stream"
    with httpx.stream("GET", url, timeout=None) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                yield event
                if event.get("type") in ("run.completed", "run.failed"):
                    break


def execute(
    agent: str | None = typer.Option(None, "--agent", help="Run only this agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan, no writes"),
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Run all enabled agents against a fresh GitHub snapshot."""
    ensure_runtime()
    repo_root = repo

    if dry_run:
        execute_dry(agent, repo_root)
        return

    workspace_id = resolve_workspace_id(repo_root)
    env_vars: dict[str, str] = {}
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if github_token:
        env_vars["GITHUB_TOKEN"] = github_token

    trigger_resp = runtime_request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/runs",
        json={"only_agent": agent, "env_vars": env_vars},
    )
    if trigger_resp.status_code != 202:
        report_error(trigger_resp)
        raise typer.Exit(1)
    run_id = trigger_resp.json()["run_id"]

    ZenveTUI(events=stream_run_events(workspace_id, run_id)).run()


@run_app.command("ls")
def ls(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
    limit: int = typer.Option(50, "--limit", help="Max number of runs to show"),
) -> None:
    """List all runs for the current workspace."""
    ensure_runtime()
    workspace_id = resolve_workspace_id(repo)
    resp = runtime_request(
        "GET", f"/api/v1/workspaces/{workspace_id}/runs", params={"limit": limit}
    )
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)

    runs = resp.json()
    if not runs:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("RUN ID", style="cyan", no_wrap=True)
    table.add_column("STARTED", style="dim")
    table.add_column("STATUS", justify="center")
    table.add_column("AGENTS")

    for run in runs:
        status = run["status"]
        if status == "done":
            status_text = Text("● done", style="green")
        else:
            status_text = Text("✗ failed", style="red")
        agent_names = "  ".join(a["agent"] for a in run["agents"])
        started = run["started_at"].replace("T", " ").replace("Z", "")
        table.add_row(run["run_id"][:12], started, status_text, agent_names)

    console.print()
    console.print(table)
    console.print()


@run_app.command("show")
def show(
    run_id: str = typer.Argument(..., help="Run id to inspect"),
    repo: Path = typer.Option(Path("."), "--repo", help="Path to the repo root"),
) -> None:
    """Show details for a specific run."""
    ensure_runtime()
    workspace_id = resolve_workspace_id(repo)
    resp = runtime_request("GET", f"/api/v1/workspaces/{workspace_id}/runs/{run_id}")
    if resp.status_code == 404:
        console.print(f"[red]✗[/red] Run [cyan]{run_id}[/cyan] not found.")
        raise typer.Exit(1)
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)

    run = resp.json()

    header = Text()
    header.append("run  ", style="dim")
    header.append(run["run_id"], style="bold cyan")
    header.append("   ")
    status_style = "bold green" if run["status"] == "done" else "bold red"
    header.append(run["status"], style=status_style)
    console.print(header)
    console.print(f"  [dim]started   {run['started_at'].replace('T', ' ').replace('Z', '')}[/dim]")
    console.print(f"  [dim]finished  {run['finished_at'].replace('T', ' ').replace('Z', '')}[/dim]")
    console.print()

    for agent in run["agents"]:
        status = agent["status"]
        if status in ("done", "completed"):
            agent_status_style = "green"
        elif status in ("needs_input", "changes_requested"):
            agent_status_style = "yellow"
        else:
            agent_status_style = "red"
        line = Text()
        line.append("  ◆ ", style="bold cyan")
        line.append(agent["agent"], style="bold")
        line.append("  ")
        line.append(status, style=agent_status_style)
        if agent.get("duration_seconds") is not None:
            line.append(f"  {agent['duration_seconds']:.1f}s", style="dim")
        console.print(line)
        if agent.get("error"):
            console.print(f"    [red]{agent['error']}[/red]")

    console.print()
