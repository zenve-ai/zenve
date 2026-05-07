from __future__ import annotations

import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table

console = Console()


def mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:4] + "..." + value[-4:]


def cmd(repo_root: Path) -> None:
    dotenv_path = repo_root / ".env"
    dotenv_vars = set(dotenv_values(dotenv_path).keys()) if dotenv_path.exists() else set()

    from zenve_cli.core.discovery import discover_agents
    from zenve_cli.core.env import load_env

    try:
        env = load_env(repo_root)
        gh_token = env.github_token
        if os.environ.get("ZENVE_GH_TOKEN"):
            gh_token_source = ".env" if "ZENVE_GH_TOKEN" in dotenv_vars else "env"
        else:
            gh_token_source = "gh auth token"
    except Exception:
        gh_token = None
        gh_token_source = "none"

    console.print(f"\n[bold]Zenve Env[/bold]  [dim]{repo_root.resolve()}[/dim]\n")

    if dotenv_path.exists():
        console.print(f"[dim].env:[/dim] {dotenv_path}")
    else:
        console.print("[dim].env:[/dim] [yellow]not found[/yellow]")

    console.print()

    # Core vars
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Variable")
    table.add_column("Value")
    table.add_column("Source")

    for key in ["ZENVE_GH_TOKEN", "ZENVE_WEBHOOK_URL", "ZENVE_WEBHOOK_SECRET"]:
        raw = os.environ.get(key)
        if raw:
            source = ".env" if key in dotenv_vars else "env"
            table.add_row(key, mask(raw), source)
        else:
            table.add_row(key, "[dim]not set[/dim]", "")

    console.print(table)
    console.print()

    # Effective GitHub token
    if gh_token:
        console.print(f"[bold]Effective GitHub token:[/bold] {mask(gh_token)}  [dim]({gh_token_source})[/dim]")
        try:
            result = subprocess.run(
                ["gh", "api", "user", "--jq", ".login"],
                capture_output=True,
                text=True,
                env={**os.environ, "GH_TOKEN": gh_token},
            )
            login = result.stdout.strip()
            if login:
                console.print(f"[bold]GitHub user:[/bold] {login}")
        except FileNotFoundError:
            pass
    else:
        console.print("[red]No GitHub token resolved.[/red] Run `gh auth login` or set ZENVE_GH_TOKEN.")

    # Per-agent token overrides
    try:
        agents = discover_agents(repo_root)
        overrides = []
        for agent in agents:
            env_key = "ZENVE_GH_" + agent.settings.slug.upper().replace("-", "_")
            raw = os.environ.get(env_key)
            if raw:
                source = ".env" if env_key in dotenv_vars else "env"
                overrides.append((env_key, agent.settings.slug, mask(raw), source))

        if overrides:
            console.print()
            console.print("[bold]Per-agent token overrides:[/bold]")
            agent_table = Table(show_header=False, box=None, padding=(0, 2))
            agent_table.add_column("Variable")
            agent_table.add_column("Agent")
            agent_table.add_column("Value")
            agent_table.add_column("Source")
            for env_key, slug, value, source in overrides:
                agent_table.add_row(env_key, f"[dim]{slug}[/dim]", value, source)
            console.print(agent_table)
    except Exception:
        pass

    console.print()
