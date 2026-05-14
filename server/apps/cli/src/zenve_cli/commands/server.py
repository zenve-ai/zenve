from __future__ import annotations

import os
import signal
from pathlib import Path

import httpx
import typer
from rich.console import Console

from zenve_cli.runtime.client import runtime_url

server_app = typer.Typer(help="Manage the zenve runtime daemon", invoke_without_command=True)
console = Console()

PID_FILE = Path.home() / ".zenve" / "runtime.pid"
LOG_FILE = Path.home() / ".zenve" / "runtime.log"


@server_app.callback(invoke_without_command=True)
def start(ctx: typer.Context) -> None:
    """Start the zenve runtime daemon in the foreground."""
    if ctx.invoked_subcommand is not None:
        return

    url = runtime_url()
    try:
        httpx.get(f"{url}/healthz", timeout=2).raise_for_status()
        console.print(f"[yellow]◆[/yellow] Runtime is already running at [cyan]{url}[/cyan]")
        raise typer.Exit(0)
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pass

    from runtime.main import main as runtime_main

    runtime_main()


def _pid_from_port() -> int | None:
    """Find the PID of the process listening on the runtime port."""
    import subprocess

    from zenve_cli.runtime.client import runtime_url

    port = runtime_url().rsplit(":", 1)[-1]
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        return int(out.splitlines()[0]) if out else None
    except (subprocess.CalledProcessError, ValueError):
        return None


@server_app.command("stop")
def stop() -> None:
    """Stop the runtime daemon."""
    pid: int | None = None

    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
    else:
        pid = _pid_from_port()
        if pid is None:
            console.print("[yellow]◆[/yellow] Runtime is not running.")
            raise typer.Exit(0)

    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        console.print(f"[green]✓[/green] Runtime (pid {pid}) stopped.")
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        console.print(f"[yellow]◆[/yellow] Process {pid} was not running. Cleaned up.")
    except PermissionError:
        console.print(f"[red]✗[/red] No permission to stop process {pid}.")
        raise typer.Exit(1)  # noqa: B904


@server_app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Stream log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """Show runtime daemon logs."""
    import subprocess

    if not LOG_FILE.exists():
        console.print(f"[dim]No log file at {LOG_FILE}[/dim]")
        raise typer.Exit(0)

    if follow:
        subprocess.run(["tail", f"-n{lines}", "-f", str(LOG_FILE)])
    else:
        subprocess.run(["tail", f"-n{lines}", str(LOG_FILE)])
