from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import typer
from rich.console import Console

console = Console()


def runtime_url() -> str:
    return os.getenv("ZENVE_RUNTIME_URL", "http://localhost:8001").rstrip("/")


def ensure_runtime() -> None:
    """Start the runtime daemon if it is not already running."""
    url = runtime_url()

    # 1. Check if already running
    try:
        httpx.get(f"{url}/healthz", timeout=2).raise_for_status()
        return
    except Exception:
        pass

    # 2. Find runtime-start next to the zenve binary (same venv/bin)
    bin_path = Path(sys.executable).parent / "runtime-start"
    if not bin_path.exists():
        console.print("[red]✗ runtime-start not found. Try reinstalling zenve.[/red]")
        raise typer.Exit(1)

    # 3. Spawn detached, log to ~/.zenve/runtime.log
    log_path = Path.home() / ".zenve" / "runtime.log"
    log_path.parent.mkdir(exist_ok=True)
    console.print("[dim]Starting zenve runtime...[/dim]")
    with open(log_path, "a") as log:
        subprocess.Popen([str(bin_path)], stdout=log, stderr=log, start_new_session=True)

    # 4. Poll /healthz up to 10s
    for _ in range(20):
        time.sleep(0.5)
        try:
            httpx.get(f"{url}/healthz", timeout=1).raise_for_status()
            console.print("[dim]Runtime ready.[/dim]")
            return
        except Exception:
            pass

    console.print(f"[red]✗ Runtime did not start in 10s. Check {log_path}[/red]")
    raise typer.Exit(1)


def runtime_request(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{runtime_url()}{path}"
    try:
        with httpx.Client(timeout=10.0) as client:
            return client.request(method, url, **kwargs)
    except httpx.ConnectError:
        console.print(
            f"[red]✗[/red] Cannot reach runtime at [cyan]{runtime_url()}[/cyan]. "
            "Is it running? Try [cyan]zenve server[/cyan]."
        )
        raise typer.Exit(1) from None


def report_error(resp: httpx.Response) -> None:
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    console.print(f"[red]✗[/red] {resp.status_code}: {detail}")


def resolve_workspace_id(repo_root: Path) -> str:
    abs_path = str(repo_root.expanduser().resolve())
    resp = runtime_request("GET", "/api/v1/workspaces")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    for w in resp.json():
        if w["path"] == abs_path:
            return w["id"]
    console.print(f"[red]✗[/red] No workspace registered at [cyan]{abs_path}[/cyan]")
    console.print("  Register it with: [cyan]zenve workspace add .[/cyan]")
    raise typer.Exit(1)
