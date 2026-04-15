from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path

import redis
from celery import Celery

from zenve_adapters.registry import AdapterRegistry
from zenve_models.adapter import RunContext

from zenve_cli.credentials import load_credentials
from zenve_cli.gateway_client import GatewayClient, GatewayError

logger = logging.getLogger(__name__)

def _build_redis_url(url: str, password: str | None) -> str:
    """Embed password into a redis URL if not already present."""
    if not password:
        return url
    from urllib.parse import urlparse, urlunparse
    p = urlparse(url)
    if p.password:
        return url  # already has a password
    netloc = f":{password}@{p.hostname}"
    if p.port:
        netloc += f":{p.port}"
    return urlunparse(p._replace(netloc=netloc))


creds = load_credentials() or {}
redis_url: str = _build_redis_url(
    creds.get("redis_url", "redis://localhost:6379/0"),
    creds.get("redis_password"),
)

celery_app = Celery("zenve_cli", broker=redis_url)
redis_client = redis.Redis.from_url(redis_url)

_adapter_registry = AdapterRegistry()

try:
    from zenve_adapters.claude_code import ClaudeCodeAdapter
    _adapter_registry.register(ClaudeCodeAdapter())
except Exception:
    pass

try:
    from zenve_adapters.open_code import OpenCodeAdapter
    _adapter_registry.register(OpenCodeAdapter())
except Exception:
    pass


def make_event_publisher(rc: redis.Redis, run_id: str):
    def on_event(event_type: str, content: str | None = None, meta: dict | None = None) -> None:
        payload = json.dumps({"event_type": event_type, "content": content, "meta": meta})
        rc.publish(f"run:{run_id}:events", payload)
    return on_event


@celery_app.task(bind=True, max_retries=3)
def execute_local_run(self, run_id: str) -> None:
    creds = load_credentials()
    if not creds:
        raise RuntimeError("No credentials found — run: zenve login")

    logger.info("[run %s] Starting", run_id)

    client = GatewayClient(creds["gateway_url"], creds["api_key"])
    try:
        ctx_data = client.get_run_context(run_id)
    except GatewayError as exc:
        logger.error("[run %s] Failed to fetch context: %s", run_id, exc)
        raise self.retry(exc=exc, countdown=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write agent files into temp dir
        for file_info in ctx_data.get("files", []):
            file_path = Path(tmpdir) / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info["content"], encoding="utf-8")

        run_ctx = ctx_data["run_context"]
        ctx = RunContext(
            agent_dir=tmpdir,
            agent_id=run_ctx["agent_id"],
            agent_slug=run_ctx["agent_slug"],
            agent_name=run_ctx["agent_name"],
            org_id=run_ctx["org_id"],
            org_slug=run_ctx["org_slug"],
            run_id=run_id,
            adapter_type=ctx_data["adapter_type"],
            adapter_config=ctx_data["adapter_config"],
            message=ctx_data["message"],
            heartbeat=ctx_data["heartbeat"],
            gateway_url=ctx_data["env_vars"].get("ZENVE_URL", creds["gateway_url"]),
            agent_token=ctx_data["env_vars"].get("ZENVE_AGENT_TOKEN", ""),
            env_vars=ctx_data["env_vars"],
            on_event=make_event_publisher(redis_client, run_id),
        )

        adapter = _adapter_registry.get(ctx.adapter_type)
        import time
        start = time.monotonic()
        result = asyncio.run(adapter.execute(ctx))
        duration = time.monotonic() - start

    logger.info("[run %s] Completed · exit_code: %s · %.1fs", run_id, result.exit_code, duration)

    client.complete_run(run_id, {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "token_usage": result.token_usage,
        "duration_seconds": duration,
    })
    client.close()
