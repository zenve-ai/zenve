# Chunk 18 — GitHub Agent Templates

## Goal
Allow agent creation from live template directories hosted in a public (or private) GitHub repo. The template repo serves as a browsable catalog: each subdirectory under `agents/` is one template. Listing templates hits the GitHub Contents API; creating an agent copies those files verbatim (no Jinja2 rendering) into the agent's directory. An optional `manifest.yaml` per template provides display metadata. This supplements (does not replace) the Jinja2 preset system from chunk 03.

## Depends On
- Chunk 03 — Agent Filesystem & Templates (ScaffoldingService, agent dir layout, settings patterns)
- Chunk 01 — Organizations CRUD (org slug, base_path resolution)
- Chunk 04 — Agents CRUD (AgentService, Agent ORM model)

## Referenced By
- Chunk 04 — Agents CRUD (new creation path via `AgentService.create_from_github_template`)

## Deliverables

### 1. Settings — `packages/config/src/zenve_config/settings.py`
Two new optional fields:
- `github_agents_repo: str | None` — owner/repo, e.g. `"myorg/agent-templates"`
- `github_token: str | None` — optional PAT for higher API rate limits

### 2. Pydantic Models — `packages/models/src/zenve_models/github_template.py`
- `GitHubTemplateSummary` — `id`, `name`, `description`, `adapter_type`
- `AgentCreateFromGitHubTemplate` — `template_id`, `name` (optional override)

### 3. Service — `packages/scaffolding/src/zenve_scaffolding/github_template_service.py`
`GitHubTemplateService(settings)` — synchronous httpx calls with module-level TTL cache (300 s).

| Method | Description |
|--------|-------------|
| `is_enabled()` | Returns `True` when `github_agents_repo` is set |
| `list_templates()` | Lists all dirs under `agents/` in the repo + reads each manifest |
| `get_template(id)` | Validates dir exists, returns `GitHubTemplateSummary` |
| `scaffold_agent_from_template(template_id, org_slug, agent_slug, base_path)` | Fetches all blobs via Trees API, writes files, ensures `memory/` and `runs/` exist |
| `cached_get(url, params)` | Module-level TTL cache wrapper around `httpx.get` |
| `list_tree_blobs(prefix)` | Recursive Trees API — one request for all blobs under a path |
| `fetch_blob_bytes(url)` | Downloads raw blob bytes |
| `read_manifest(template_id)` | Fetches and parses `manifest.yaml`; returns `{}` on 404 |
| `auth_headers()` | Builds GitHub API headers; adds `Authorization` if token set |

**Error mapping:**
- GitHub 404 → HTTP 404
- GitHub 401/403 → HTTP 422 "Cannot access GitHub repo"
- Rate limit (429) → HTTP 429 propagated
- `httpx.RequestError` → HTTP 502 "GitHub API unreachable"

### 4. Dependency Function — `packages/services/src/zenve_services/__init__.py`
`get_github_template_service(settings) -> GitHubTemplateService` factory.
`get_agent_service` updated to inject it.

### 5. Routes — `apps/api/src/api/routes/`

**`github_template.py`** — listing router:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/github-templates` | List all templates (503 if not configured) |
| GET | `/api/v1/github-templates/{id}` | Get single template (503 if not configured) |

**`agent.py`** — creation endpoint added alongside `/from-preset`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/orgs/{org_id}/agents/from-github-template` | Create agent from GitHub template |

Auth: JWT + membership check (same as `/from-preset`).

## Config
| Variable | Description |
|----------|-------------|
| `GITHUB_AGENTS_REPO` | `owner/repo` of the agent templates repo |
| `GITHUB_TOKEN` | Optional PAT; increases rate limit from 60 to 5000 req/h |

## Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| No Jinja2 rendering | Files copied verbatim | Templates are pre-written, ready-to-use markdown; rendering adds complexity with no benefit |
| Module-level cache | `dict[str, tuple[data, expires_at]]` with 300 s TTL | Avoids hammering GitHub API on every request without requiring Redis |
| Trees API for scaffolding | Single recursive tree fetch | Minimizes API calls (one vs. N for N files) when creating an agent |
| 503 when unconfigured | Both listing and creation return 503 | Clear signal to operators vs. silent empty list |
| Supplements presets | Both systems coexist | Avoids migration burden; live GitHub catalog and bundled presets serve different use cases |

## Change Log
| Date | Change | Reason |
|------|--------|--------|
| 2026-04-23 | Initial implementation | User request: live GitHub catalog for agent templates |
