# API Refactor 04 — Repo-Backed Agent API

## Goal

Replace the DB-backed agent CRUD with a repo-backed API. Agents are read from and written to the user's GitHub repo via the GitHub App. No agent data in the DB.

## New: Repo models (`packages/models/src/zenve_models/repo.py`)
- `AgentSummary` — lightweight agent info from `settings.json`
- `AgentDetail` — full agent info + file existence flags (SOUL/AGENTS/HEARTBEAT)
- `RunSummary`, `RunDetail` — run data from committed JSON
- `ProjectSettings` — from `.zenve/settings.json`

## New: Repo reader service (`packages/services/src/zenve_services/repo_reader.py`)
Uses `zenve_utils.github` under the hood:
- `list_agents(project) -> list[AgentSummary]` — lists `.zenve/agents/`, reads each `settings.json`
- `get_agent(project, name) -> AgentDetail`
- `read_agent_file(project, name, relpath) -> bytes` — with path-traversal guard
- `list_runs(project, name) -> list[RunSummary]` — dir listing of `.zenve/agents/{name}/runs/`
- `get_run(project, name, run_id) -> RunDetail` — reads JSON
- `get_project_settings(project) -> ProjectSettings` — reads `.zenve/settings.json`

## New: Agent service (`packages/services/src/zenve_services/agent.py`)
Repo-coupled replacement. Composes `ScaffoldingService` + `RepoWriterService` + `repo_reader`:
- `create(project, data: AgentCreate) -> AgentDetail` — render templates → commit `.zenve/agents/{slug}/*`
- `create_from_preset(project, data: AgentCreateFromPreset) -> AgentDetail`
- `update(project, name, data: AgentUpdate) -> AgentDetail` — read current `settings.json`, merge, commit
- `delete(project, name) -> None` — commit deletion of `.zenve/agents/{name}/`
- `write_file(project, name, relpath, content)` — single-file commit

## Refactor: Scaffolding service (`packages/scaffolding/`)
- Refactor `ScaffoldingService.scaffold_agent_dir` to return `dict[str, bytes]` (in-memory file tree) instead of writing to disk
- Drop `seed_default_templates` and `copy_traversable`
- Templates bundled via `importlib.resources`

## Reworked routes (`apps/api/src/api/routes/agent.py`)
Prefix: `/api/v1/projects/{project_id}/agents`

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

Plus on project: `GET /api/v1/projects/{id}/settings` — read `.zenve/settings.json`

Auth: dual-dep pattern (JWT+membership OR API key).

## Dependencies
- Requires plan 03 (GitHub App + repo writer)

## Verification
1. `GET /api/v1/projects/{id}/agents` → `[]` (empty repo)
2. `POST /api/v1/projects/{id}/agents {name: "dev", preset: "developer"}` → 201, check repo for `.zenve/agents/dev/*` in one commit
3. `GET /api/v1/projects/{id}/agents` → `[{name: "dev", ...}]`
4. `PATCH /api/v1/projects/{id}/agents/dev {enabled: false}` → commits update
5. `PUT /api/v1/projects/{id}/agents/dev/files/SOUL.md` → commits file
6. `PUT /projects/{id}/agents/dev/files/../../../etc/passwd` → 400 (path-traversal guard)
7. `DELETE /api/v1/projects/{id}/agents/dev` → agent dir removed, list returns `[]`
