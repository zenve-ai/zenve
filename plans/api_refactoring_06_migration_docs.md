# API Refactor 06 — DB Migration + Docs Update

## Goal

Generate the Alembic baseline migration and update all documentation to reflect the new architecture.

## DB Migration

No `alembic/versions/` directory yet — this is a clean baseline.

### Dev (SQLite)
- `Base.metadata.create_all` on startup handles new schema
- Delete `zenve.db` to reset

### Prod (Postgres)
Generate a single baseline migration:
```bash
uv run alembic revision --autogenerate -m "baseline: projects model, drop agents/runs"
```

Verify it:
- (a) renames `organizations` → `projects`
- (b) renames `memberships.org_id` + `api_keys.org_id` → `project_id`
- (c) drops `agents`, `runs`, `run_events`
- (d) drops `projects.base_path` + `projects.redis_worker_url`
- (e) adds three `github_*` columns
- Use batch-op mode so SQLite column renames work

## Docs Update

### Rewrite
- `docs/architecture/00-overview.md` — new vision, data model
- `docs/architecture/04-agents-crud.md` — repo-backed agent API

### Rename + Rewrite
- `01-organizations-crud.md` → `01-projects-crud.md` (no `base_path`, with GitHub fields)
- `02-api-key-auth.md` — project terminology and FKs
- `17-org-websocket.md` → `03-project-websocket.md` (broadcast-only, keyed by project)

### Keep + Prune
- `14-health-observability.md` — remove Celery/worker probes

### Delete
- `03-agent-filesystem-templates.md`
- `05-adapter-interface.md`
- `06-claude-code-adapter.md`
- `07-celery-run-execution.md`
- `08-runs-crud.md`
- `09-agent-runtime-tokens.md`
- `10-heartbeat-scheduler.md`
- `11-collaborations-data-model.md`
- `12-collaboration-execution-engine.md`
- `13-collaboration-api.md`
- `15-run-event-system.md`
- `16-org-git-versioning.md`

### New docs
- `05-github-app-integration.md` — app credentials, installation tokens, `commit_tree`, webhook verification
- `06-repo-backed-read-api.md` — read endpoints, path-traversal guard, no-cache semantics
- `07-zenve-webhook-receiver.md` — HMAC verification, project routing, WS broadcast, no persistence

### Update `server/CLAUDE.md`
- Auth table: `/api/v1/orgs` → `/api/v1/projects`; `get_current_org` → `get_current_project`
- Remove references to agents/runs/celery/adapters/templates in DB/services/routes

## Dependencies
- Should be done last, after plans 01–05 are complete

## Verification
- Alembic migration applies cleanly on fresh Postgres
- All docs reference `projects`, not `organizations`
- No references to deleted features (Celery, Redis ACL, DB agents/runs)
