from __future__ import annotations

import asyncio
import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.text import Text

from zenve_adapters import AdapterRegistry
from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_adapters.open_code import OpenCodeAdapter
from zenve_cli.commands.snapshot import git_remote_slug
from zenve_cli.console import ZenveTUI
from zenve_cli.core.config import ConfigError, load_project_settings
from zenve_cli.core.discovery import DiscoveryError, discover_agents
from zenve_cli.core.env import EnvError, load_env
from zenve_cli.events import types as et
from zenve_cli.events.emitter import EventEmitter
from zenve_cli.integrations.github.client import GitHubClient
from zenve_cli.integrations.github.snapshot import build_snapshot, write_snapshot
from zenve_cli.models.run_result import RunResultFile
from zenve_cli.runtime.commit import (
    GitError,
    commit_agents,
    commit_zenve_dir,
    fetch_origin,
    has_dirty_outside_zenve,
    has_dirty_zenve,
    remote_branch_exists,
)
from zenve_cli.runtime.executor import DryRunResult, reconcile_claims
from zenve_cli.runtime.parallel import run_all

console = Console()


def build_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(ClaudeCodeAdapter())
    registry.register(OpenCodeAdapter())
    return registry


def cmd(
    repo_root: Path = Path("."),
    agent: str | None = None,
    dry_run: bool = False,
) -> None:
    """Run all enabled agents against a fresh GitHub snapshot."""
    status = console.status("[cyan]starting zenve…[/cyan]", spinner="dots")
    status.start()
    try:
        status.update("[cyan]loading env & config…[/cyan]")
        env = load_env(repo_root)
        project = load_project_settings(repo_root)
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
    repo = git_remote_slug(repo_root)
    if not repo:
        status.stop()
        typer.echo("✗ Could not determine repo. Ensure git remote origin is a GitHub URL.")
        raise typer.Exit(1)

    if has_dirty_outside_zenve(repo_root):
        status.stop()
        typer.echo("✗ Local repo has uncommitted changes outside .zenve/.")
        typer.echo("  Zenve cannot run safely because generated worktrees/snapshots may be based on stale or mixed state.")
        typer.echo("")
        typer.echo("  Commit, stash, or discard your changes, then run again.")
        raise typer.Exit(1)

    if has_dirty_zenve(repo_root):
        status.stop()
        if not typer.confirm("Local .zenve/ has uncommitted changes. Commit and push them before running?", default=True):
            typer.echo("✗ Aborted. Commit, stash, or discard your .zenve/ changes, then run again.")
            raise typer.Exit(1)
        status.start()
        status.update("[cyan]committing .zenve/ changes…[/cyan]")
        try:
            commit_zenve_dir(
                repo_root,
                f"{project.commit_message_prefix} update .zenve config",
                branch=project.default_branch,
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

    if not remote_branch_exists(repo_root, project.default_branch):
        status.stop()
        typer.echo(f"✗ Remote branch origin/{project.default_branch} not found after fetch.")
        raise typer.Exit(1)

    status.stop()

    env_vars = {"ZENVE_RUN_ID": env.run_id, "GH_TOKEN": env.github_token}

    if dry_run:
        emitter = EventEmitter(
            repo_root=repo_root,
            run_id=env.run_id,
            webhook_url=env.webhook_url,
            webhook_secret=env.webhook_secret,
            on_event=None,
        )
        emitter.emit(
            et.RUN_STARTED,
            data={"agents": [a.name for a in agents], "repo": repo, "dry_run": True},
        )

        with GitHubClient(env.github_token, repo) as gh:
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

            registry = build_registry()
            results = asyncio.run(
                run_all(
                    agents=agents,
                    snapshot=snapshot,
                    project=project,
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

        def row(label: str, value: str, value_style: str = "white") -> None:
            line = Text()
            line.append(f"    {label:<{label_w}}", style="dim")
            line.append(value, style=value_style)
            console.print(line)

        console.print()
        for ag in agents:
            slug_line = Text()
            slug_line.append("  ◆ ", style="bold cyan")
            slug_line.append(ag.name, style="bold white")
            console.print(slug_line)

            dr = dry_lookup.get(ag.name)
            if dr is None:
                console.print("    [dim]no result[/dim]")
                console.print()
                continue

            row("name", ag.settings.name)
            row("label", dr.label, "cyan")
            row("model", str(ag.settings.adapter_config.get("model", "")), "dim white")

            if dr.item is not None:
                pick_text = f"{dr.item.kind} #{dr.item.number}: {dr.item.title}"
                row("would pick", pick_text)

                ctx_dict = {
                    k: v for k, v in dataclasses.asdict(dr.context).items() if not callable(v)
                }
                ctx_json = json.dumps(ctx_dict, indent=2)
                indented = "\n".join(f"    {line}" for line in ctx_json.splitlines())
                console.print()
                console.print("    context", style="dim")
                console.print(indented, style="dim")
            else:
                row("would pick", "nothing to do", "dim")

            console.print()

        emitter.emit(et.RUN_COMPLETED, data={"dry_run": True})
        return

    # ── Live run — launch TUI ─────────────────────────────────────────────────

    def run_fn(on_event: Callable[[dict], None]) -> None:
        emitter = EventEmitter(
            repo_root=repo_root,
            run_id=env.run_id,
            webhook_url=env.webhook_url,
            webhook_secret=env.webhook_secret,
            on_event=on_event,
        )
        emitter.emit(
            et.RUN_STARTED,
            data={"agents": [a.name for a in agents], "repo": repo, "dry_run": False},
        )

        with GitHubClient(env.github_token, repo) as gh:
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

            reconcile_claims(gh, snapshot, repo_root)

            registry = build_registry()
            results = asyncio.run(
                run_all(
                    agents=agents,
                    snapshot=snapshot,
                    project=project,
                    repo_root=repo_root,
                    run_id=env.run_id,
                    registry=registry,
                    gh=gh,
                    emitter=emitter,
                    env_vars=env_vars,
                    dry_run=False,
                )
            )

        summaries = [r for r in results if isinstance(r, RunResultFile)]
        summary = ", ".join(
            f"{r.agent}: {r.status}{' #' + str(r.item.number) if r.item else ''}" for r in summaries
        )

        emitter.emit(et.RUN_COMMITTING)
        committed = False
        try:
            committed = commit_agents(
                repo_root=repo_root,
                run_id=env.run_id,
                prefix=project.commit_message_prefix,
                branch=project.default_branch,
                summary=summary,
            )
        except GitError as exc:
            emitter.emit(et.RUN_FAILED, data={"error": str(exc)})

        emitter.emit(
            et.RUN_COMPLETED,
            data={"committed": committed, "summary": summary, "agents": len(summaries)},
        )

    ZenveTUI(run_fn=run_fn, schedule=project.run_schedule).run()
