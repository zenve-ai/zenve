# Plan: zenve CLI

## Context

Zenve is a self-hosted AI agent gateway. This task adds `zenve-cli` — a CLI package users install on their machines, currently covering auth (`zenve login`) and the daemon (`zenve daemon start`), with room for more features later.

The daemon authenticates via API key, detects local runtimes (claude/codex/opencode), and executes agent runs dispatched via Celery + Redis — using the **same `ClaudeCodeAdapter`** from `zenve_adapters` as the gateway does, just without the DB/WebSocket layer (replaced by HTTP calls to the gateway).

---

## Placement: `server/apps/cli/`

Placing it under `server/apps/` makes it a uv workspace member with access to `zenve-adapters`, `zenve-models`, and `zenve-config`. No custom adapter layer needed — we reuse the existing ones directly.

---

## File Structure

```
server/apps/cli/
  pyproject.toml
  src/zenve_cli/
    __init__.py
    cli.py              # typer app: login, daemon start/stop/status
    credentials.py      # load/save ~/.zenve/credentials.json
    gateway_client.py   # sync httpx wrapper for gateway endpoints
    worker.py           # Celery app + execute_local_run task
    runtime_detect.py   # shutil.which checks for known CLIs
```

No `core/` subdirectory — we import directly from `zenve_adapters` and `zenve_models`.

---

## Implementation Plan

### 1. `server/pyproject.toml` changes
- Add `"apps/cli"` to `[tool.uv.workspace] members`
- Add `zenve-cli = { workspace = true }` to `[tool.uv.sources]`

### 2. `pyproject.toml`
```toml
[project]
name = "zenve-cli"
requires-python = ">=3.11"
dependencies = [
  "typer[all]>=0.12",
  "httpx>=0.27",
  "celery[redis]>=5.3",
  "redis>=5.0",
  "python-dotenv>=1.0",
  "zenve-adapters",
  "zenve-models",
]

[project.scripts]
zenve = "zenve_cli.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 3. `credentials.py`
- `CREDENTIALS_PATH = Path.home() / ".zenve" / "credentials.json"`
- `save_credentials(data: dict)` — mkdir + write JSON
- `load_credentials() -> dict | None` — None if missing
- Credentials shape: `gateway_url`, `api_key`, `org_slug`, `redis_url`, `connected_at`
- **Note:** `redis_url` here is the org-scoped worker URL (`redis://worker.{slug}:{password}@...`)
  returned once by `POST /orgs`. It uses Redis ACL — the worker user has locked-down
  permissions (own queue keys + pub/sub only). See gateway `RedisACLService`.

### 4. `gateway_client.py`
- `GatewayClient(gateway_url: str, api_key: str)` using `httpx.Client` (sync)
- Headers: `Authorization: Bearer <api_key>`
- `verify_credentials() -> dict` — `GET /api/v1/orgs/me`; returns org data (must include `redis_url`)
- `register_worker(org_slug, queue, runtimes)` — `POST /api/v1/internal/worker/register`
- `get_run_context(run_id) -> dict` — `GET /api/v1/internal/runs/{run_id}/context`
- `complete_run(run_id, payload: dict)` — `POST /api/v1/internal/runs/{run_id}/complete`
- Raises `GatewayError(status_code, body)` on 4xx/5xx, logged before raising

### 5. `runtime_detect.py`
```python
KNOWN_RUNTIMES = {"claude": "claude_code", "codex": "codex", "opencode": "opencode"}

def detect_runtimes() -> list[str]:
    """Return list of binary names (e.g. 'claude') that are on PATH."""
    return [bin for bin in KNOWN_RUNTIMES if shutil.which(bin)]
```

### 6. `worker.py`

Loads credentials at import time, configures Celery broker and Redis client:
```python
creds = load_credentials()
celery_app = Celery("zenve_cli", broker=creds["redis_url"])
redis_client = redis.Redis.from_url(creds["redis_url"])
```

`make_event_publisher(redis_client, run_id)` — returns a sync callable matching `on_event` signature:
```python
def make_event_publisher(redis_client, run_id: str):
    def on_event(event_type: str, content: str | None, meta: dict | None) -> None:
        payload = json.dumps({"event_type": event_type, "content": content, "meta": meta})
        redis_client.publish(f"run:{run_id}:events", payload)
    return on_event
```

Channel name: `run:{run_id}:events`

Task `execute_local_run(self, run_id: str)`:
1. Log `[run {run_id}] Starting · adapter: {adapter_type}`
2. Build `GatewayClient` from credentials
3. `ctx_data = client.get_run_context(run_id)` — catch `GatewayError`, log, `raise self.retry()` or fail cleanly
4. Write files from `ctx_data["files"]` to `tempfile.TemporaryDirectory`
5. Build `RunContext` from `zenve_models.adapter`:
   ```python
   RunContext(
       agent_dir=tmpdir,
       agent_id=ctx_data["run_context"]["agent_id"],
       agent_slug=ctx_data["run_context"]["agent_slug"],
       agent_name=ctx_data["run_context"]["agent_name"],
       org_id=ctx_data["run_context"]["org_id"],
       org_slug=ctx_data["run_context"]["org_slug"],
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
   ```
6. Look up adapter: `adapter = AdapterRegistry.get(ctx.adapter_type)` using `zenve_adapters.registry`
7. `result = asyncio.run(adapter.execute(ctx))` inside `try/finally` for tempdir cleanup
8. `client.complete_run(run_id, {exit_code, stdout, stderr, token_usage, duration_seconds})`
9. Log `[run {run_id}] Completed · exit_code: {N} · {Xs}`

### 7. `cli.py`
- `app = typer.Typer(name="zenve")`
- `daemon_app = typer.Typer()`; `app.add_typer(daemon_app, name="daemon")`

**`@app.command() login`**:
1. `typer.prompt("Gateway URL")` + `typer.prompt("API Key", hide_input=True)`
2. `GatewayClient(url, key).verify_credentials()` — on failure print `✗ …` and `raise typer.Exit(1)`
3. Save credentials including `redis_url` from response
4. Print `✓ Authenticated as workspace: {org_slug}` + `✓ Credentials saved to ~/.zenve/credentials.json`

**`@daemon_app.command() start`**:
1. `load_credentials()` — if None print `✗ Not logged in. Run: zenve login`, exit 1
2. Print `✓ Loaded credentials from ~/.zenve/credentials.json`
3. Print `✓ Connected to {host}`
4. `runtimes = detect_runtimes()` — print each known binary: `  claude ✓` or `  codex ✗`
5. `GatewayClient.register_worker(org_slug, f"worker.{org_slug}", runtimes)`
6. Print `✓ Worker listening on queue: worker.{org_slug}` + `  Ready. Waiting for runs...`
7. `celery_app.worker_main(["worker", "-Q", f"worker.{org_slug}", "--loglevel=info"])`

**`stop` / `status`**: `typer.echo("not yet implemented")`

---

### 8. Gateway — Redis subscriber (new)

A background task starts on gateway startup, subscribes to `run:*:events` via Redis pub/sub pattern subscribe, and for each message does exactly what `RunExecutor.on_event` does today:
1. `RunEventService.create(run_id, event_type, content, meta)` — persist to DB
2. `ws_manager.broadcast(org_id, {"type": "run.event", "data": ...})` — push to UI WebSocket clients

The subscriber needs `org_id` to broadcast — it can look this up from the run record using `run_id`.

Implementation: async task launched with `asyncio.create_task` in the FastAPI `lifespan` handler, using `redis.asyncio` (already available via Celery's Redis dep).

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Placement | `server/apps/cli/` | uv workspace → reuse zenve-adapters, zenve-models directly |
| Adapter reuse | Import `ClaudeCodeAdapter` from `zenve_adapters` | Same execution behavior as gateway manual trigger |
| Async in Celery | `asyncio.run(adapter.execute(ctx))` | ClaudeCodeAdapter.execute() is async; Celery tasks are sync |
| RunContext | `zenve_models.adapter.RunContext` | Same type, no custom dataclass needed |
| on_event | Redis pub/sub `PUBLISH run:{run_id}:events` | Daemon has no DB/WebSocket; gateway subscriber handles persist + broadcast |
| Run dispatch | Celery + Redis broker | Persistent task queue; survives daemon restarts |
| Event streaming | Redis pub/sub (not HTTP) | Fire-and-forget per event; no HTTP overhead; reuses existing Redis connection |

---

## Files to Modify

- `server/pyproject.toml` — add `apps/cli` to workspace members + sources

---

## Verification

```bash
cd server
uv sync
zenve login                # interactive prompt → writes ~/.zenve/credentials.json
zenve daemon start         # detects runtimes, registers, starts Celery worker
```
