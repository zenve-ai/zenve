# API Refactor — DB-Centric → Repo-Centric

## Context

The Zenve CLI (`apps/cli`) already runs the entire agent lifecycle locally: it reads `.zenve/agents/*` from a git repo, executes agents in parallel, and commits run results (`runs/{run_id}.json`) back to the same repo. State lives in the repo — no server needed for execution.

The server API, however, still owns `agents`, `runs`, and `run_events` in the DB, plus a heavy stack (Celery, adapters, filesystem scaffolding, Redis ACL, templates, presets) built around a DB-centric agent model. That architecture is now redundant with the CLI.

This refactor **demotes the API from a run-executor to a thin repo-facing surface**. The API no longer stores or executes runs, but it still **writes** to the repo — it scaffolds new agents (renders templates + pushes a commit via the GitHub App) and edits existing agent files. Reads come straight from GitHub on every request.

- **Stays in DB:** users, memberships, API keys, and a new `projects` table (renamed from `organizations`; one project = one GitHub repo).
- **Moves to the user's repo:** agent definitions (`.zenve/agents/{name}/settings.json`, SOUL/AGENTS/HEARTBEAT, memory, runs).
- **Removed entirely (API-only code):** Celery, worker routes, run dispatch, Redis ACL, and the API's agent/run DB services/routes. The API no longer executes runs.
- **Kept for the CLI (same monorepo):** `packages/adapters/` and `packages/models/src/zenve_models/adapter.py` (`RunContext`, `AdapterRegistry`, `ClaudeCodeAdapter`, `OpenCodeAdapter`). The API stops importing them; the CLI still does.
- **Kept for API scaffolding:** `packages/scaffolding/` (template rendering), `packages/models/src/zenve_models/template.py` + `preset.py`, `packages/services/.../template.py`. Refactored to produce an in-memory `{path: bytes}` tree instead of writing to local disk — committed to GitHub by a new `RepoWriterService`.
- **New:** GitHub App integration for reading + committing repo files, a `/projects/{id}/agents/*` read+write API, a `/webhooks/zenve-events` receiver that verifies HMAC and broadcasts to UI WebSockets (no persistence).

Intended outcome: a small, boring API that owns auth + project-to-repo mapping, and gets out of the way of the CLI.

## Scope decisions (confirmed with user)

| Decision | Choice |
|---|---|
| Org/repo model | Rename `organizations` → `projects`. One project = one GitHub repo. |
| GitHub auth | GitHub App (installation tokens). |
| API execution role | Read-only + webhook receiver. No Celery, no workers. |
| UI read path | On-demand from GitHub contents API. No DB cache/sync. |
| Event persistence | Broadcast-only to WS. Historical events come from committed `runs/{id}.json`. |

## Out of scope (flagged for follow-up)

- **UI rewrite** — 16 UI files hit `/orgs`, `/agents`, `/runs` via RTK Query. This PR breaks them. Either bundle a UI PR or ship a temporary `/orgs` alias; do not merge the server PR standalone.
- **CLI change** — CLI must include a project identifier in webhook posts so the API can route to the right WS subscribers. Recommend `X-Zenve-Project-Id` header (cheapest).

## Implementation plan

### Phase A — Delete dead code (API-only; do NOT touch CLI-used code)

**Keep, do not delete** — still imported by `apps/cli`:

- `packages/adapters/` (entire package) — `zenve_cli.runtime.executor`, `runtime.parallel`, `commands.start` import `AdapterRegistry`, `ClaudeCodeAdapter`, `OpenCodeAdapter`.
- `packages/models/src/zenve_models/adapter.py` — `RunContext` is imported by `zenve_cli.runtime.executor`.

**Keep, but refactor for repo-writes** — still needed by the API to scaffold agents:

- `packages/scaffolding/` — refactor `ScaffoldingService.scaffold_agent_dir` to return an in-memory `dict[str, bytes]` of rendered files (paths relative to agent dir) instead of writing to local disk. Drop `seed_default_templates` and `copy_traversable` (no more `templates_dir` on disk); templates are bundled inside the package via `importlib.resources`. Keep `RUN.md.j2` → `HEARTBEAT.md.j2` naming aligned with the CLI spec.
- `packages/services/src/zenve_services/template.py` — keep; lists available templates so the UI can offer a picker.
- `packages/services/src/zenve_services/preset.py` (new, extracted) — keep preset manifests for `create_from_preset` calls.
- `packages/models/src/zenve_models/template.py`, `preset.py` — keep. Request/response shapes for template/preset pickers.
- `packages/models/src/zenve_models/agent.py` — **trim, don't delete.** Keep `AgentCreate`, `AgentCreateFromPreset`, `AgentUpdate`, `AgentFileWrite`; these are API request bodies, not ORM-coupled. Drop `AgentResponse` (replaced by repo-read `AgentSummary` / `AgentDetail` in `repo.py`).

**Delete wholesale** — API-only, verified unreferenced by the CLI:

- `packages/models/src/zenve_models/`: `run.py`, `run_event.py`, `worker.py`. **Do not delete `adapter.py`, `agent.py`, `template.py`, `preset.py`.**
- `packages/services/src/zenve_services/`: `agent.py` (DB-coupled version; replaced by a new repo-coupled `AgentService`), `filesystem.py`, `redis_acl.py`, `run.py`, `run_dispatch.py`, `run_event.py`, `run_executor.py`.
- `packages/utils/src/zenve_utils/redis.py`.
- `apps/api/src/api/routes/`: `run.py`, `worker.py`. Keep `agent.py`, `preset.py`, `template.py` but rewrite them against the new repo-backed services.

Then:

- Clean `packages/services/src/zenve_services/__init__.py` of dependency factories for deleted services.
- Prune `apps/api/src/api/lifespan.py` of Celery / adapter registry / Redis / filesystem-bootstrap hooks. The API lifespan no longer instantiates `AdapterRegistry` or seeds template directories.
- Audit `justfile` and any `docker-compose.yml` for Celery/Redis services; prune.

### Phase B — Rename `organizations` → `projects`

Table/class/file/route/dependency rename. All of:

- `packages/db/src/zenve_db/models.py` — rename `Organization` → `Project` (table `projects`). Drop `Agent`, `Run`, `RunEvent` classes. Drop `base_path`, `redis_worker_url` from the new `Project` table. Add `github_installation_id: int | None`, `github_repo: str | None` (format `owner/name`), `github_default_branch: str | None`. On `Membership` and `ApiKeyRecord`: rename `org_id` → `project_id`, relationship `organization` → `project`.
- `packages/models/src/zenve_models/org.py` → rename to `project.py`; rename models `OrgCreate/Update/Response` → `ProjectCreate/Update/Response`. Drop `base_path`/`redis_worker_url`. Add a `ProjectGitHubConnect(installation_id, repo)` request model.
- `packages/services/src/zenve_services/org.py` → rename to `project.py`; rename `OrgService` → `ProjectService`. Creation becomes a pure DB insert + owner membership; drop all filesystem bootstrap (`base_path`, git init, template copy).
- `packages/services/src/zenve_services/api_key_auth.py` — rename `get_current_org` → `get_current_project`; return type `(Project, ApiKeyRecord)`.
- `packages/services/src/zenve_services/api_key.py` — reparent FKs from `org_id` to `project_id`.
- `packages/services/src/zenve_services/membership.py` — rename fields/params (`org_id` → `project_id`).
- `apps/api/src/api/routes/org.py` → rename to `project.py`; prefix `/api/v1/projects`.
- `apps/api/src/api/routes/api_key.py` — nest under `/api/v1/projects/{id}/api-keys` for consistency.
- `apps/api/src/api/routes/__init__.py`, `main.py` — update imports + `include_router` calls.

### Phase C — GitHub App integration (new)

New settings in `packages/config/src/zenve_config/settings.py`: add `github_app_id: int | None`, `github_app_private_key: str | None`, `github_webhook_secret: str | None`, `zenve_webhook_secret: str | None`. Remove now-dead settings: `data_dir`, `templates_dir`, `gateway_url`, `setup_token`, `redis_url`, `redis_password`.

New file `packages/utils/src/zenve_utils/github.py`:

- `mint_installation_token(installation_id) -> str` — JWT-sign app assertion with the private key, POST `/app/installations/{id}/access_tokens`, cache 5-min TTL.
- `get_repo_file(installation_id, repo, path, ref=None) -> bytes` — contents API.
- `list_repo_dir(installation_id, repo, path, ref=None) -> list[dict]`.
- `commit_tree(installation_id, repo, branch, files: dict[str, bytes | None], message: str) -> str` — the write primitive. Uses the git data API (create blobs → create tree → create commit → update ref) so many files land in **one commit**. A `None` value marks a deletion. Returns the new commit SHA.
- `verify_hmac_sha256(body, signature, secret) -> bool` — shared primitive for both GitHub and Zenve webhooks.

New file `packages/services/src/zenve_services/github.py`: `GitHubService` with `connect_project(project, installation_id, repo)` (validates the app can read the repo before persisting) and `disconnect(project)`.

New file `packages/services/src/zenve_services/repo_writer.py`: `RepoWriterService` wraps `commit_tree` and handles higher-level operations: `scaffold_agent(project, agent_slug, rendered_files, commit_message)`, `delete_agent(project, agent_slug)`, `write_file(project, agent_slug, relpath, content)`. Applies path-traversal guards before calling `commit_tree`.

New endpoints in `apps/api/src/api/routes/project.py`:

- `POST /api/v1/projects/{id}/github/connect` — body `{installation_id, repo}`. Validates + persists.
- `DELETE /api/v1/projects/{id}/github/disconnect` — clears the fields.

### Phase D — Repo-backed agent API (read + write)

New Pydantic models in `packages/models/src/zenve_models/repo.py`: `AgentSummary`, `AgentDetail`, `RunSummary`, `RunDetail`, `ProjectSettings`. Keep `AgentCreate`, `AgentCreateFromPreset`, `AgentUpdate`, `AgentFileWrite` in the existing `agent.py`.

New service `packages/services/src/zenve_services/repo_reader.py` (reuses `zenve_utils.github`):

- `list_agents(project) -> list[AgentSummary]` — lists `.zenve/agents/`, reads each `settings.json`.
- `get_agent(project, name) -> AgentDetail` — `settings.json` + existence of SOUL/AGENTS/HEARTBEAT.
- `read_agent_file(project, name, relpath) -> bytes` — with path-traversal guard (resolved path must stay under `.zenve/agents/{name}/`).
- `list_runs(project, name) -> list[RunSummary]` — dir listing of `.zenve/agents/{name}/runs/`.
- `get_run(project, name, run_id) -> RunDetail` — reads JSON.
- `get_project_settings(project) -> ProjectSettings` — reads `.zenve/settings.json`.

New `AgentService` in `packages/services/src/zenve_services/agent.py` (repo-coupled; replaces the deleted DB-coupled version). Composes `ScaffoldingService` + `RepoWriterService` + `repo_reader`:

- `create(project, data: AgentCreate) -> AgentDetail` — render templates → dict of files → commit `.zenve/agents/{slug}/*` via `RepoWriterService.scaffold_agent`. Fails if agent dir already exists in repo.
- `create_from_preset(project, data: AgentCreateFromPreset) -> AgentDetail` — same, with preset defaults.
- `update(project, name, data: AgentUpdate) -> AgentDetail` — read current `settings.json`, merge changes, commit back.
- `delete(project, name) -> None` — commit a tree that deletes `.zenve/agents/{name}/` recursively.
- `write_file(project, name, relpath, content)` — commit a single-file edit (SOUL.md, memory/*.md, etc).

Reworked routes in `apps/api/src/api/routes/agent.py` — prefix `/api/v1/projects/{project_id}/agents`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | List agents (read from repo) |
| POST | `/` | Scaffold new agent (commits to repo) |
| POST | `/from-preset` | Scaffold from preset (commits to repo) |
| GET | `/{name}` | Agent detail (read from repo) |
| PATCH | `/{name}` | Update `settings.json` (commits) |
| DELETE | `/{name}` | Remove agent dir (commits) |
| GET | `/{name}/files` | List files under agent dir |
| GET | `/{name}/files/{path:path}` | Read a file (read from repo) |
| PUT | `/{name}/files/{path:path}` | Write a file (commits) |
| GET | `/{name}/runs` | List runs |
| GET | `/{name}/runs/{run_id}` | One run JSON |

Plus on the project itself:

- `GET /api/v1/projects/{id}/settings` — read `.zenve/settings.json`.

Auth: accept either JWT+membership or API key (dual-dep pattern), matching UI + programmatic needs.

### Phase E — Webhook receiver + WS broadcast

New route `apps/api/src/api/routes/webhook.py`:

- `POST /api/v1/webhooks/zenve-events` — verify `X-Zenve-Signature` (HMAC-SHA256 with `zenve_webhook_secret`), read `X-Zenve-Project-Id` to scope broadcast, push JSON body to connected WS clients for that project. No DB writes.
- `POST /api/v1/webhooks/github` (behind `github_webhook_secret` if set) — handle `installation`, `installation_repositories` to auto-disconnect projects whose installation was uninstalled.

Trim `packages/services/src/zenve_services/ws_manager.py` down to three methods: `connect(project_id, ws)`, `disconnect(ws)`, `broadcast(project_id, event)`. Remove all run-lifecycle coupling.

Update `apps/api/src/api/routes/ws.py` — key subscriptions by `project_id`, JWT-auth unchanged.

### Phase F — DB migration

There's no `alembic/versions/` directory yet, so this is a clean baseline.

- **Dev (default SQLite at `zenve.db`)**: `Base.metadata.create_all` on startup (see `lifespan.py`) already handles the new schema after Phase B. Delete `zenve.db` to reset.
- **Prod (Postgres)**: generate a single baseline migration:

  ```bash
  uv run alembic revision --autogenerate -m "baseline: projects model, drop agents/runs"
  ```

  Verify it (a) renames `organizations` → `projects`, (b) renames `memberships.org_id` + `api_keys.org_id` → `project_id`, (c) drops `agents`, `runs`, `run_events`, (d) drops `projects.base_path` + `projects.redis_worker_url`, (e) adds the three `github_*` columns. Use batch-op mode so SQLite column renames work.

### Phase G — Docs

Rewrite `/Users/2020756/Projects/python/zenve/docs/architecture/`:

- **Rewrite** `00-overview.md` (new vision, new data model, new chunk table).
- **Rename + rewrite** `01-organizations-crud.md` → `01-projects-crud.md` (no `base_path`, with GitHub fields).
- **Rewrite** `02-api-key-auth.md` — project terminology and FKs.
- **Rename + rewrite** `17-org-websocket.md` → `03-project-websocket.md` (broadcast-only, keyed by project).
- **Keep** `14-health-observability.md` — prune Celery/worker probes.
- **Delete** chunks `03-agent-filesystem-templates.md`, `05-adapter-interface.md`, `06-claude-code-adapter.md`, `07-celery-run-execution.md`, `08-runs-crud.md`, `09-agent-runtime-tokens.md`, `10-heartbeat-scheduler.md`, `11-collaborations-data-model.md`, `12-collaboration-execution-engine.md`, `13-collaboration-api.md`, `15-run-event-system.md`, `16-org-git-versioning.md`.
- **Rewrite** `04-agents-crud.md` — same filename, but now it describes the repo-backed agent API (scaffold-on-create, GitHub commit-push on every mutation, reads via contents API, no DB table).
- **New chunks**:
  - `05-github-app-integration.md` — app credentials, installation token minting, `commit_tree` write primitive, webhook verification, config surface.
  - `06-repo-backed-read-api.md` — read endpoints + path-traversal guard + no-cache semantics.
  - `07-zenve-webhook-receiver.md` — HMAC verification, project routing, WS broadcast, no persistence.

Update `/Users/2020756/Projects/python/zenve/server/CLAUDE.md`:

- Auth table: `/api/v1/orgs` → `/api/v1/projects`; `get_current_org` → `get_current_project`.
- Remove every reference to agents/runs/celery/adapters/templates in DB/services/routes.
- Drop "Agent Integration" row from chunk template.

## Critical files

- `server/packages/db/src/zenve_db/models.py`
- `server/packages/config/src/zenve_config/settings.py`
- `server/apps/api/src/api/main.py`
- `server/apps/api/src/api/lifespan.py`
- `server/apps/api/src/api/routes/__init__.py`
- `server/packages/services/src/zenve_services/__init__.py`
- `server/packages/services/src/zenve_services/api_key_auth.py`
- `server/CLAUDE.md`
- `docs/architecture/00-overview.md`

## Verification

End-to-end smoke test after implementation:

1. `rm server/zenve.db && just dev`.
2. `POST /api/v1/auth/signup` → JWT.
3. `POST /api/v1/projects` with JWT → new project row, no filesystem side-effects.
4. Install Zenve GitHub App on an **empty** test repo. Note `installation_id`.
5. `POST /api/v1/projects/{id}/github/connect {installation_id, repo}` → 200, fields populated.
6. `GET /api/v1/projects/{id}/agents` → returns `[]` (repo has no `.zenve/agents/`).
7. `POST /api/v1/projects/{id}/agents {name: "dev", preset: "developer"}` → 201. Inspect the repo on GitHub: `.zenve/agents/dev/{settings.json,SOUL.md,AGENTS.md,HEARTBEAT.md,memory/…}` created in **one commit** by the Zenve App user.
8. `GET /api/v1/projects/{id}/agents` → returns `[{name: "dev", ...}]` read live from the repo.
9. `PATCH /api/v1/projects/{id}/agents/dev {enabled: false}` → commit updates `settings.json`; GET returns the new value.
10. `PUT /api/v1/projects/{id}/agents/dev/files/SOUL.md` with new content → commit; GET returns the new content.
11. Simulate a CLI run: drop a `runs/run_test.json` into the repo (manually or via the CLI). `GET /api/v1/projects/{id}/agents/dev/runs/run_test` → returns parsed JSON.
12. Open WS subscribed to `project_id`.
13. `curl` the webhook endpoint with a valid HMAC, `X-Zenve-Project-Id` header, and `{type: "agent.started", ...}` body → WS client receives broadcast; no DB rows written (verify `sqlite3 zenve.db "SELECT count(*) FROM sqlite_master WHERE name IN ('agents','runs','run_events');"` returns 0).
14. Tamper the HMAC → 401, no broadcast.
15. Path-traversal unit test: `PUT /projects/{id}/agents/dev/files/../../../etc/passwd` → 400; no commit.
16. `DELETE /api/v1/projects/{id}/agents/dev` → agent dir removed from repo in one commit; subsequent list returns `[]`.
17. `DELETE /projects/{id}/github/disconnect` → GH fields nulled; subsequent agent list returns 409 or 404.

## Open risks

- **UI breakage.** 16 UI files call `/orgs`, `/agents`, `/runs` via RTK Query. This PR must ship alongside a UI PR or with a temporary `/orgs` alias. Confirm stance before merge.
- **CLI webhook payload.** Per `apps/cli/ARCHITECTURE.md`, CLI posts `{run_id, timestamp, type, agent, data}` — no project identifier. CLI change required: add `X-Zenve-Project-Id` header. Coordinate.
- **Installation token caching.** In-process cache only; multi-replica deploys re-mint per process. Acceptable short-term (low QPS); revisit if deploying > 1 replica.
- **Alembic baseline on SQLite.** Column renames require batch-op mode; verify autogenerate emits it (or hand-edit).
- **`just dev` / docker-compose.** May reference Celery/Redis; prune in lockstep with package deletion to avoid startup crashes.
