from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from zenve_adapters import AdapterRegistry
from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_adapters.open_code import OpenCodeAdapter
from zenve_cli.commands.snapshot import repo_slug_from_url
from zenve_cli.core.config import ConfigError, load_project_settings
from zenve_cli.core.discovery import DiscoveryError, discover_agents
from zenve_cli.core.env import EnvError, load_env
from zenve_cli.events import types as et
from zenve_cli.events.emitter import EventEmitter
from zenve_cli.github.client import GitHubClient
from zenve_cli.github.snapshot import build_snapshot, write_snapshot
from zenve_cli.runtime.commit import GitError, commit_and_push
from zenve_cli.runtime.parallel import run_all


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

    repo = project.repo or repo_slug_from_url(env.repo_url)
    if not repo:
        typer.echo("✗ Could not determine repo (check settings.repo or ZENVE_REPO_URL).")
        raise typer.Exit(1)

    emitter = EventEmitter(
        repo_root=repo_root,
        run_id=env.run_id,
        webhook_url=env.webhook_url,
        webhook_secret=env.webhook_secret,
    )
    emitter.emit(
        et.RUN_STARTED,
        data={"agents": [a.name for a in agents], "repo": repo, "dry_run": dry_run},
    )

    env_vars = {
        "GITHUB_TOKEN": env.github_token,
        "ANTHROPIC_API_KEY": env.anthropic_api_key,
        "ZENVE_RUN_ID": env.run_id,
        "ZENVE_REPO_URL": env.repo_url,
    }

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

        bot_login = ""
        if not dry_run:
            try:
                bot_login = gh.viewer_login()
            except Exception as exc:
                typer.echo(f"✗ Could not resolve viewer login: {exc}")
                raise typer.Exit(1) from exc

        registry = build_registry()
        results = asyncio.run(
            run_all(
                agents=agents,
                snapshot=snapshot,
                project=project,
                run_id=env.run_id,
                registry=registry,
                gh=gh,
                bot_login=bot_login,
                emitter=emitter,
                env_vars=env_vars,
                dry_run=dry_run,
            )
        )

    if dry_run:
        emitter.emit(et.RUN_COMPLETED, data={"dry_run": True})
        typer.echo("✓ dry-run complete")
        return

    summaries = [r for r in results if r is not None]
    summary = ", ".join(
        f"{r.agent}: {r.status}{' #' + str(r.item.number) if r.item else ''}"
        for r in summaries
    )

    emitter.emit(et.RUN_COMMITTING, data={"summary": summary})
    try:
        committed = commit_and_push(
            repo_root=repo_root,
            run_id=env.run_id,
            prefix=project.commit_message_prefix,
            branch=project.default_branch,
            summary=summary,
        )
    except GitError as exc:
        emitter.emit(et.RUN_FAILED, data={"error": str(exc), "stage": "commit"})
        typer.echo(f"✗ commit/push failed: {exc}")
        raise typer.Exit(1) from exc

    emitter.emit(
        et.RUN_COMPLETED,
        data={"committed": committed, "summary": summary, "agents": len(summaries)},
    )
    typer.echo(f"✓ run {env.run_id} complete ({len(summaries)} agent(s))")
