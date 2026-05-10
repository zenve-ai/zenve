# CLAUDE.md — zenve Runtime

Local-machine FastAPI daemon. Long-running process that owns workspaces (registered local repos with `.zenve/`) and exposes them over HTTP to clients (TUI, web frontend, future scheduler). Sibling app to `apps/api/` — same architectural rules apply.

Port: **8001** (API app uses 8000).

## Status

Scaffold only. Read endpoints over the on-disk format the CLI already writes. **No** auth, **no** scheduler, **no** run triggering, **no** SSE/WebSocket yet — those land in subsequent iterations.

The CLI is **not** modified. `zenve run` continues to work standalone.

## Structure

```
src/runtime/
├── main.py             # FastAPI app, exception handlers, CORS, router include
├── lifespan.py         # constructs WorkspaceService + RunService, stashes on app.state
├── models/
│   ├── errors.py       # ZenveError + domain exceptions
│   ├── workspace.py    # Workspace, WorkspaceCreate, WorkspaceDetail
│   └── run.py          # WorkspaceRunSummary, WorkspaceRunDetail, RunItem, TokenUsage, PipelineTransition
├── services/
│   ├── __init__.py     # get_workspace_service, get_run_service dependency factories
│   ├── workspace_service.py
│   └── run_service.py
└── routes/
    ├── core.py         # GET / and /healthz
    ├── workspace.py    # /api/v1/workspaces
    └── run.py          # /api/v1/workspaces/{id}/runs
```

## Endpoints

All under `/api/v1`. No auth.

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | `{ok, service, version}` |
| POST | `/workspaces` | 201 `Workspace` (validates `<path>/.zenve/settings.json` exists) |
| GET | `/workspaces` | `list[Workspace]` |
| GET | `/workspaces/{id}` | `WorkspaceDetail` (re-reads `settings.json` each call; lists agent slugs) |
| DELETE | `/workspaces/{id}` | 204 (registry only — never touches `.zenve/`) |
| GET | `/workspaces/{id}/runs?agent=&limit=` | `list[WorkspaceRunSummary]` sorted by `started_at` desc |
| GET | `/workspaces/{id}/runs/{run_id}` | `WorkspaceRunDetail` |

## Layer Rules

Same as `apps/api/` (see [server/CLAUDE.md](../../CLAUDE.md)):

- **Routes are thin** — no business logic, no file I/O, no JSON parsing. Only `Depends(get_*_service)` then call.
- **Services** raise domain exceptions from `runtime.models.errors` (`NotFoundError`, `ConflictError`, `ValidationError`, `ExternalError`). The handlers in `main.py` translate them to HTTP. **Never** raise `HTTPException` from a service.
- **Pydantic models** live in `runtime/models/`, never inside `routes/`.
- **Dependency factories** (`get_workspace_service`, `get_run_service`) live only in `runtime/services/__init__.py` — never in route files.
- **No DB imports** in routes. (Runtime has no DB — registry is filesystem.)

## Workspace Registry

`~/.zenve/workspaces.json`:

```json
{
  "version": 1,
  "workspaces": [
    {"id": "a1b2c3d4e5f6", "path": "/abs/path", "registered_at": "2026-..."}
  ]
}
```

- Owned by `WorkspaceService`; loaded on construction in `lifespan`
- Mutations serialized via `threading.Lock`
- Atomic write: `tmp` → `os.replace`
- Path normalization: `expanduser().resolve()` before storing — duplicate detection works regardless of how the user typed the path

## On-Disk Contract

The runtime is a **reader** of the format the CLI writes. See [`apps/cli/CLAUDE.md`](../cli/CLAUDE.md) for the full `.zenve/` convention. Relevant pieces:

- `<path>/.zenve/settings.json` → `WorkspaceDetail` fields
- `<path>/.zenve/agents/*/` → agent slugs
- `<path>/.zenve/agents/{slug}/runs/{run_id}.json` (`RunResultFile` shape) → `WorkspaceRunSummary` / `WorkspaceRunDetail`

The runtime DTOs are intentionally decoupled from `zenve_cli` Python code — the JSON format is the contract.

## Dev Commands

```bash
just runtime       # start with hot reload (port 8001)
just runtime-dev   # alias / variant if added later
```

Smoke test:
```bash
curl localhost:8001/healthz
curl -X POST localhost:8001/api/v1/workspaces \
  -H 'Content-Type: application/json' \
  -d '{"path":"/path/to/repo/with/.zenve"}'
curl localhost:8001/api/v1/workspaces
```

## Adding a Feature

Same flow as `apps/api/`:
1. **Pydantic model** → `apps/runtime/src/runtime/models/{domain}.py`
2. **Service** → `apps/runtime/src/runtime/services/{domain}_service.py` (filesystem-backed services do not take `db: Session`)
3. **Dependency factory** → `apps/runtime/src/runtime/services/__init__.py`
4. **Route** → `apps/runtime/src/runtime/routes/{domain}.py`
5. **Register router** → `apps/runtime/src/runtime/routes/__init__.py` + `main.py`

## Roadmap (out of scope for current scaffold)

- Scheduler — fire runs based on each workspace's `run_schedule` (cron). The CLI already has the cron parsing logic; lift into a service.
- Run triggering — `POST /workspaces/{id}/runs` to spawn `zenve run` subprocesses
- SSE / WebSocket streaming of live events
- Filesystem watcher on each `settings.json` so schedule edits hot-reload
- Auth (local-only `127.0.0.1` is the only "auth" today)
