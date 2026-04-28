from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_adapters.open_code import OpenCodeAdapter
from zenve_cli.commands.snapshot import git_remote_slug
from zenve_cli.core.config import ConfigError, load_project_settings, zenve_dir
from zenve_cli.core.discovery import DiscoveryError, discover_agents

console = Console()


def cmd(repo_root: Path) -> None:
    """Run setup checks and report pass/fail."""
    console.print("\n[bold]Zenve Doctor[/bold]\n")

    checks: list[tuple[str, bool, str | None]] = []
    critical_failures = 0

    # Check 1: .zenve/ directory exists (critical)
    zdir = zenve_dir(repo_root)
    if zdir.exists():
        checks.append(("Directory setup (.zenve/)", True, None))
    else:
        checks.append(("Directory setup (.zenve/)", False, "run `zenve init` to scaffold"))
        critical_failures += 1

    # Check 2: settings.json exists & valid (critical)
    settings = None
    try:
        settings = load_project_settings(repo_root)
        project_name = getattr(settings, "project", None) or getattr(settings, "name", None)
        detail = project_name or None
        checks.append(("Valid zenve settings (.zenve/settings.json)", True, detail))
    except ConfigError as exc:
        checks.append(("Valid zenve settings (.zenve/settings.json)", False, str(exc)))
        critical_failures += 1

    # Check 3: at least one agent defined (critical)
    try:
        agents = discover_agents(repo_root)
        count = len(agents)
        if count > 0:
            checks.append(("Agent definitions (.zenve/agents/)", True, f"{count} agent{'s' if count != 1 else ''} found"))
        else:
            checks.append(("Agent definitions (.zenve/agents/)", False, "no agents found"))
            critical_failures += 1
    except DiscoveryError as exc:
        checks.append(("Agent definitions (.zenve/agents/)", False, str(exc)))
        critical_failures += 1

    # Check 4: gh CLI installed (critical)
    gh_installed = shutil.which("gh") is not None
    if gh_installed:
        checks.append(("GitHub CLI installed (gh)", True, None))
    else:
        checks.append(("GitHub CLI installed (gh)", False, "install from https://cli.github.com"))
        critical_failures += 1

    # Check 5: gh authenticated (critical)
    gh_token: str | None = None
    if gh_installed:
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
            )
            gh_token = result.stdout.strip() or None
            if gh_token:
                checks.append(("GitHub authentication (gh auth)", True, None))
            else:
                checks.append(("GitHub authentication (gh auth)", False, "run `gh auth login`"))
                critical_failures += 1
        except subprocess.CalledProcessError:
            checks.append(("GitHub authentication (gh auth)", False, "run `gh auth login`"))
            critical_failures += 1
    else:
        checks.append(("GitHub authentication (gh auth)", False, "gh CLI not installed"))
        critical_failures += 1

    # Check 6: repo can be resolved from git remote (critical)
    repo_slug = git_remote_slug(repo_root)
    if repo_slug:
        checks.append(("GitHub repository (git remote origin)", True, repo_slug))
    else:
        checks.append((
            "GitHub repository (git remote origin)",
            False,
            "run `git remote add origin <github-url>`",
        ))
        critical_failures += 1

    # Check 7: claude_code adapter healthy (advisory)
    claude_ok = asyncio.run(ClaudeCodeAdapter().health_check())
    checks.append(("Claude Code adapter", claude_ok, None if claude_ok else "not available"))

    # Check 8: open_code adapter healthy (advisory)
    open_ok = asyncio.run(OpenCodeAdapter().health_check())
    checks.append(("Open Code adapter", open_ok, None if open_ok else "not available"))

    # Warn if both adapters fail
    both_adapters_failed = not claude_ok and not open_ok

    # Render results
    for label, ok, detail in checks:
        if ok is True:
            icon = "[green]✓[/green]"
        elif ok is False:
            icon = "[red]✗[/red]"
        else:
            icon = "[yellow]~[/yellow]"

        suffix = f"  [dim]{detail}[/dim]" if detail else ""
        console.print(f"  {icon} {label}{suffix}")

    if both_adapters_failed:
        console.print("\n  [yellow]warning:[/yellow] no usable adapter found — both claude_code and open_code unavailable")

    console.print()
    if critical_failures == 0:
        console.print("[green]All checks passed.[/green]")
    elif critical_failures == 1:
        console.print("[red]1 critical issue found.[/red]")
    else:
        console.print(f"[red]{critical_failures} critical issues found.[/red]")

    console.print()

    if critical_failures > 0:
        raise typer.Exit(code=1)
