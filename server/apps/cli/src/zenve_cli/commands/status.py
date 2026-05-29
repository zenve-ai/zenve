from __future__ import annotations

import os
from pathlib import Path

import httpx
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_cli.commands.agent import iter_agent_dirs, load_agent_settings
from zenve_cli.runtime.client import runtime_url
from zenve_cli.utils.time import time_ago
from zenve_engine.config import zenve_dir

console = Console()


def web_url() -> str:
    return os.getenv("ZENVE_WEB_URL", "http://localhost:5173").rstrip("/")


def check_service(url: str, path: str = "/") -> bool:
    try:
        resp = httpx.get(f"{url}{path}", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


def agent_run_map(repo_root: Path, runtime_up: bool) -> dict[str, dict]:
    if not runtime_up:
        return {}
    abs_path = str(repo_root.expanduser().resolve())
    try:
        resp = httpx.get(f"{runtime_url()}/api/v1/workspaces", timeout=2.0)
        if resp.status_code != 200:
            return {}
        workspace_id = next((w["id"] for w in resp.json() if w["path"] == abs_path), None)
        if not workspace_id:
            return {}
        resp2 = httpx.get(f"{runtime_url()}/api/v1/workspaces/{workspace_id}/runs/latest", timeout=2.0)
        if resp2.status_code != 200:
            return {}
        run = resp2.json()
        if not run:
            return {}
        return {a["agent"]: a for a in run.get("agents", [])}
    except Exception:
        return {}


def cmd(repo_root: Path = Path(".")) -> None:
    """Show system status and agents."""
    rurl = runtime_url()
    wurl = web_url()
    runtime_up = check_service(rurl, "/healthz")
    web_up = check_service(wurl)

    console.print()

    # ── Services ──────────────────────────────────────────────────────────────
    for label, url, up in [("runtime", rurl, runtime_up), ("web", wurl, web_up)]:
        line = Text("  ")
        if up:
            line.append("●", style="bold green")
            line.append(f"  {label:<10}", style="bold")
            line.append(url, style="cyan link " + url)
        else:
            line.append("○", style="dim red")
            line.append(f"  {label:<10}", style="dim")
            line.append(url, style="dim")
            line.append("   not running", style="dim red")
        console.print(line)

    if not zenve_dir(repo_root).exists():
        console.print()
        console.print("  [dim]No .zenve/ found — run [bold]zenve init[/bold] to get started.[/dim]")
        console.print()
        return

    # ── Agents ────────────────────────────────────────────────────────────────
    agent_dirs = iter_agent_dirs(repo_root)
    if not agent_dirs:
        console.print()
        console.print("  [dim]No agents configured.[/dim]")
        console.print()
        return

    console.print()

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("AGENT", style="cyan", no_wrap=True)
    table.add_column("ENABLED", justify="center")
    table.add_column("LAST RUN", justify="center")
    table.add_column("WHEN", style="dim")

    run_agents = agent_run_map(repo_root, runtime_up)

    for d in agent_dirs:
        s = load_agent_settings(d)
        name = d.name if s is None else s.name

        if s is None:
            enabled_text = Text("—", style="dim")
        elif s.enabled:
            enabled_text = Text("● on", style="bold green")
        else:
            enabled_text = Text("○ off", style="dim red")

        agent_info = run_agents.get(d.name)
        if agent_info is None:
            table.add_row(name, enabled_text, Text("—", style="dim"), "—")
            continue

        run_status = agent_info.get("status", "?")
        if run_status == "completed":
            run_text = Text("● done", style="green")
        elif run_status == "failed":
            run_text = Text("✗ failed", style="red")
        elif run_status == "running":
            run_text = Text("◌ running", style="cyan")
        elif run_status == "skipped":
            run_text = Text("— skipped", style="dim")
        else:
            run_text = Text(run_status, style="dim")

        started = agent_info.get("started_at", "")
        when = time_ago(started) if started else "—"
        table.add_row(name, enabled_text, run_text, when)

    console.print(table)
    console.print()
