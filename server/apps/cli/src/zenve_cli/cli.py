from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import typer

from zenve_cli.credentials import CREDENTIALS_PATH, load_credentials, save_credentials
from zenve_cli.gateway_client import GatewayClient, GatewayError
from zenve_cli.runtime_detect import KNOWN_RUNTIMES, detect_runtimes

app = typer.Typer(name="zenve", help="Zenve CLI")
daemon_app = typer.Typer(help="Daemon management commands")
app.add_typer(daemon_app, name="daemon")


@app.command()
def login() -> None:
    """Authenticate with a Zenve gateway and save credentials."""
    gateway_url = typer.prompt("Gateway URL")
    api_key = typer.prompt("API Key")

    client = GatewayClient(gateway_url, api_key)
    try:
        org_data = client.verify_credentials()
    except GatewayError as exc:
        typer.echo(f"✗ Authentication failed: {exc.body}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"✗ Could not reach gateway: {exc}")
        raise typer.Exit(1) from exc
    finally:
        client.close()

    org_slug = org_data.get("slug", "unknown")
    redis_worker_url = org_data.get("redis_worker_url")

    save_credentials(
        {
            "gateway_url": gateway_url,
            "api_key": api_key,
            "org_slug": org_slug,
            "redis_worker_url": redis_worker_url,
            "connected_at": datetime.now(UTC).isoformat(),
        }
    )

    typer.echo(f"✓ Authenticated as workspace: {org_slug}")
    typer.echo(f"✓ Credentials saved to {CREDENTIALS_PATH}")


@daemon_app.command("start")
def daemon_start() -> None:
    """Start the Zenve local daemon worker."""
    creds = load_credentials()
    if not creds:
        typer.echo("✗ Not logged in. Run: zenve login")
        raise typer.Exit(1)

    typer.echo(f"✓ Loaded credentials from {CREDENTIALS_PATH}")

    host = urlparse(creds["gateway_url"]).netloc
    typer.echo(f"✓ Connected to {host}")

    runtimes = detect_runtimes()
    for bin_name in KNOWN_RUNTIMES:
        mark = "✓" if bin_name in runtimes else "✗"
        typer.echo(f"  {bin_name} {mark}")

    org_slug = creds["org_slug"]
    queue = f"worker.{org_slug}"

    from zenve_cli.gateway_client import GatewayClient, GatewayError

    client = GatewayClient(creds["gateway_url"], creds["api_key"])
    try:
        client.register_worker(org_slug, queue, runtimes)
    except GatewayError as exc:
        typer.echo(f"✗ Worker registration failed: {exc.body}")
        raise typer.Exit(1) from exc
    finally:
        client.close()

    typer.echo(f"✓ Worker listening on queue: {queue}")
    typer.echo("  Ready. Waiting for runs...")

    from zenve_cli.worker import celery_app

    celery_app.worker_main(["worker", "-Q", queue, "--loglevel=info"])


@daemon_app.command("stop")
def daemon_stop() -> None:
    """Stop the Zenve local daemon worker."""
    typer.echo("not yet implemented")


@daemon_app.command("status")
def daemon_status() -> None:
    """Show the Zenve local daemon status."""
    typer.echo("not yet implemented")
