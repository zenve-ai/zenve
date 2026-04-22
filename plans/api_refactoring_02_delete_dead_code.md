# API Refactor 02 — Delete Dead Code

## Goal

Remove all API-only code related to runs, workers, Celery, Redis ACL, and filesystem scaffolding. The API no longer executes runs — the CLI does that.

## What to keep (still used by CLI)
- `packages/adapters/` (entire package) — imported by `apps/cli`
- `packages/models/src/zenve_models/adapter.py` — `RunContext` imported by CLI

## What to keep (still needed for API scaffolding)
- `packages/scaffolding/` — will be refactored later (plan 04) but don't delete
- `packages/services/src/zenve_services/template.py` — template listing for UI
- `packages/models/src/zenve_models/template.py`, `preset.py` — request/response shapes
- `packages/models/src/zenve_models/agent.py` — trim but keep `AgentCreate`, `AgentCreateFromPreset`, `AgentUpdate`, `AgentFileWrite`. Drop `AgentResponse`

## Delete wholesale

### Models (`packages/models/src/zenve_models/`)
- `run.py`
- `run_event.py`
- `worker.py`

### Services (`packages/services/src/zenve_services/`)
- `agent.py` (DB-coupled version — will be replaced by repo-coupled version in plan 04)
- `filesystem.py`
- `redis_acl.py`
- `run.py`
- `run_dispatch.py`
- `run_event.py`
- `run_executor.py`

### Utils (`packages/utils/src/zenve_utils/`)
- `redis.py`

### Routes (`apps/api/src/api/routes/`)
- `run.py`
- `worker.py`

### DB models (`packages/db/src/zenve_db/models.py`)
- Drop `Agent`, `Run`, `RunEvent` ORM classes

## Cleanup after deletion
- Clean `packages/services/src/zenve_services/__init__.py` — remove dependency factories for deleted services
- Clean `packages/models/src/zenve_models/__init__.py` — remove deleted exports
- Prune `apps/api/src/api/lifespan.py` — remove Celery / adapter registry / Redis / filesystem-bootstrap hooks
- Prune `apps/api/src/api/routes/__init__.py` — remove deleted route imports
- Audit `justfile` and `docker-compose.yml` for Celery/Redis services; prune

## Dependencies
- Should be done after plan 01 (org → projects rename) to avoid double-touching files

## Verification
- Server starts cleanly: `rm server/zenve.db && just dev`
- No import errors
- Auth/project/membership/api-key routes still work
- `sqlite3 zenve.db "SELECT count(*) FROM sqlite_master WHERE name IN ('agents','runs','run_events');"` returns 0
