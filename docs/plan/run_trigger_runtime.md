# Plan: Run Triggering in Runtime

## Context

`zenve-engine` is a standalone package with `run()` as its public API.
`apps/runtime` is a local FastAPI daemon (port 8001) that currently does **reads only** —
workspace registry + run file reads. This plan adds run triggering.

## Architecture Decision

`RunTriggerService` lives in `server/apps/runtime/src/runtime/services/run_trigger_service.py`, **not** in
`packages/services/`. Reasons:

- It depends on `zenve-engine`, which is heavy and unused by `apps/api`
- It is stateful (in-memory active runs dict) — tied to the runtime process lifecycle
- It is not reusable across apps

The dependency factory lives in `runtime/services/__init__.py` (reads from `request.app.state`), not in
any shared package.

## Steps

### 1 — `zenve-engine` dependency (DONE)

`zenve-engine` is already declared in `server/apps/runtime/pyproject.toml`:

```toml
dependencies = [
  ...,
  "zenve-engine",
]

[tool.uv.sources]
zenve-engine = { workspace = true }
```

No changes needed.

### 2 — Pydantic models (`server/apps/runtime/src/runtime/models/run.py`)

Add to the existing file:

```python
class RunTriggerRequest(BaseModel):
    only_agent: str | None = None
    env_vars: dict[str, str] | None = None

class RunTriggerResponse(BaseModel):
    run_id: str
    status: Literal["queued"]
```

The engine already writes `RunResultFile` JSONs to disk, so the existing
`GET .../runs/{run_id}` can be polled — no new result model needed.

### 3 — `RunTriggerService` (`server/apps/runtime/src/runtime/services/run_trigger_service.py`)

Responsibilities:
- Holds `dict[str, str]` in memory: `run_id → status` (`queued | running | done | failed`)
- `trigger(workspace_id, req) -> RunTriggerResponse`:
  1. Calls `WorkspaceService.detail()` to get `project_dir` and `repo`
  2. Resolves `GITHUB_TOKEN` from env
  3. Generates `run_id` (uuid4 hex)
  4. Marks status as `queued`
  5. Submits `zenve_engine.run(...)` to a `ThreadPoolExecutor` (engine is sync + blocking)
  6. On completion: updates status to `done` or `failed`
  7. Returns `RunTriggerResponse(run_id=run_id, status="queued")` immediately

Error mapping (engine raises before any side effects):
- `DirtyTreeError` → raise `ValidationError`
- `MissingRemoteBranchError` → raise `ExternalError`
- `EngineError` → raise `ExternalError`

The `on_event` callback passed to `engine.run()` logs each event via the standard logger.
Later it can push to a per-run SSE queue (additive, no interface change needed).

### 4 — Wire in lifespan (`server/apps/runtime/src/runtime/lifespan.py`)

```python
from runtime.services.run_trigger_service import RunTriggerService

trigger_service = RunTriggerService(workspace_service)
app.state.trigger_service = trigger_service
```

Shutdown: call `trigger_service.shutdown()` which calls `executor.shutdown(wait=False)`.

### 5 — Dependency factory (`server/apps/runtime/src/runtime/services/__init__.py`)

Add alongside the existing `get_run_service`:

```python
def get_trigger_service(request: Request) -> RunTriggerService:
    return request.app.state.trigger_service
```

### 6 — Route (`server/apps/runtime/src/runtime/routes/run.py`)

Add to existing router:

```
POST /api/v1/workspaces/{workspace_id}/runs  →  202 RunTriggerResponse
```

Client flow:
1. `POST /workspaces/{id}/runs` → receive `run_id`
2. Poll `GET /workspaces/{id}/runs/{run_id}` until the result file appears on disk

### 7 — Register route

`server/apps/runtime/src/runtime/routes/__init__.py` already exports `run_router` — no change
needed as the new endpoint goes on the same router.

## File Map

```
server/apps/runtime/src/runtime/
├── models/
│   └── run.py                      # MODIFIED — add RunTriggerRequest, RunTriggerResponse
├── services/
│   ├── __init__.py                 # MODIFIED — add get_trigger_service factory
│   └── run_trigger_service.py      # NEW — RunTriggerService
├── routes/
│   └── run.py                      # MODIFIED — add POST endpoint
└── lifespan.py                     # MODIFIED — construct + stash RunTriggerService
```

## Out of Scope (Roadmap)

- SSE / WebSocket streaming — `on_event` is the hook, wiring it is additive
- Run cancellation — needs process handle or future tracking
- Scheduler — cron-triggered runs (already in runtime CLAUDE.md roadmap)
- Auth — runtime is localhost-only for now
