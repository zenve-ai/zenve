from __future__ import annotations

import os

import httpx
import typer
from rich.console import Console

console = Console()


def runtime_url() -> str:
    return os.getenv("ZENVE_RUNTIME_URL", "http://localhost:8001").rstrip("/")


def runtime_request(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{runtime_url()}{path}"
    try:
        with httpx.Client(timeout=10.0) as client:
            return client.request(method, url, **kwargs)
    except httpx.ConnectError:
        console.print(
            f"[red]✗[/red] Cannot reach runtime at [cyan]{runtime_url()}[/cyan]. "
            "Is it running? Try [cyan]just runtime[/cyan]."
        )
        raise typer.Exit(1) from None


def report_error(resp: httpx.Response) -> None:
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    console.print(f"[red]✗[/red] {resp.status_code}: {detail}")
