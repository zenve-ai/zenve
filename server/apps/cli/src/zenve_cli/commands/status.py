from __future__ import annotations

import json
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


def latest_run(agent_path: Path) -> dict | None:
    runs_dir = agent_path / "runs"
    if not runs_dir.exists():
        return None
    files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


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

    for d in agent_dirs:
        s = load_agent_settings(d)
        name = d.name if s is None else s.name

        if s is None:
            enabled_text = Text("—", style="dim")
        elif s.enabled:
            enabled_text = Text("● on", style="bold green")
        else:
            enabled_text = Text("○ off", style="dim red")

        run = latest_run(d)
        if run is None:
            table.add_row(name, enabled_text, Text("—", style="dim"), "—")
            continue

        run_status = run.get("status", "?")
        if run_status == "done":
            run_text = Text("● done", style="green")
        elif run_status == "failed":
            run_text = Text("✗ failed", style="red")
        elif run_status == "running":
            run_text = Text("◌ running", style="cyan")
        else:
            run_text = Text(run_status, style="dim")

        started = run.get("started_at", "")
        when = time_ago(started) if started else "—"
        table.add_row(name, enabled_text, run_text, when)

    console.print(table)
    console.print()
