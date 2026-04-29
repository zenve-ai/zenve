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
from zenve_cli.core.config import ConfigError, load_project_settings
from zenve_cli.core.console import ZenveTUI
from zenve_cli.core.discovery import DiscoveryError, discover_agents
from zenve_cli.core.env import EnvError, load_env
from zenve_cli.events import types as et
from zenve_cli.events.emitter import EventEmitter
from zenve_cli.integrations.github.client import GitHubClient
from zenve_cli.integrations.github.snapshot import build_snapshot, write_snapshot
from zenve_cli.models.run_result import RunResultFile
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
    try:
        env = load_env()
        project = load_project_settings(repo_root)
        agents = discover_agents(repo_root, only=agent)
    except EnvError as exc:
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc
    except (ConfigError, DiscoveryError) as exc:
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc

    if not agents:
        typer.echo("No enabled agents to run.")
        raise typer.Exit(0)

    repo = git_remote_slug(repo_root)
    if not repo:
        typer.echo("✗ Could not determine repo. Ensure git remote origin is a GitHub URL.")
        raise typer.Exit(1)

    env_vars = {"ZENVE_RUN_ID": env.run_id}

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
            f"{r.agent}: {r.status}{' #' + str(r.item.number) if r.item else ''}"
            for r in summaries
        )
        emitter.emit(
            et.RUN_COMPLETED,
            data={"committed": False, "summary": summary, "agents": len(summaries)},
        )

    ZenveTUI(run_fn=run_fn).run()
