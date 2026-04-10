# Chunk 04 — Agents CRUD

## Goal
Implement the Agent entity: ORM model, service, REST routes including file management endpoints.

## Depends On
- Chunk 01 (Organizations)
- Chunk 02 (API Key Auth — routes require auth; scopes `agents:read` / `agents:write`)
- Chunk 03 (Filesystem & Templates — agent creation scaffolds directory via `FilesystemService`)

## Referenced By
- Chunk 05 (Adapter Interface — adapters receive an `Agent` record and its `dir_path`)
- Chunk 08 (Runs CRUD — runs are FK-linked to `agents.id`)

## Deliverables

### 1. ORM Model — `db/models.py`

Add `Agent` table:

```
agents
  id              UUID PK
  org_id          UUID FK → organizations
  name            VARCHAR NOT NULL       -- unique within org
  slug            VARCHAR NOT NULL       -- unique within org
  dir_path        VARCHAR NOT NULL       -- absolute path to agent dir on disk
  adapter_type    VARCHAR NOT NULL       -- validated against KNOWN_ADAPTER_TYPES
  adapter_config  JSON                   -- adapter-specific settings (model, flags)
  skills          JSON                   -- ["code_review", "testing", "deployment"]
  status          VARCHAR NOT NULL       -- "active" | "inactive" | "archived"
  heartbeat_interval_seconds  INT DEFAULT 0  -- 0 = disabled
  last_heartbeat_at  TIMESTAMP NULL
  created_at      TIMESTAMP
  updated_at      TIMESTAMP
```

Constraints: `UniqueConstraint("org_id", "name")`, `UniqueConstraint("org_id", "slug")`.
Relationship: `Organization.agents` ↔ `Agent.organization`.

**Status values (canonical):** `active`, `inactive`, `archived`.
- `inactive` replaces the earlier "paused".
- `error` is not stored as a status; it is surfaced in the Run record (chunk 08), not on the agent.

**`KNOWN_ADAPTER_TYPES`** (module-level constant in `services/agent.py`):
```
KNOWN_ADAPTER_TYPES = ["claude_code", "codex", "anthropic_api"]
```
`adapter_type` is validated against this list on create; unrecognised values are rejected with 422.

### 2. Pydantic Models — `models/agent.py`

```python
class AgentCreate(BaseModel):
    name: str
    adapter_type: str                    # must be in KNOWN_ADAPTER_TYPES
    adapter_config: dict = {}
    skills: list[str] = []
    heartbeat_interval_seconds: int = 0
    template: str = "default"           # Jinja2 template name (chunk 03)
    role: str | None = None             # passed to template vars

class AgentUpdate(BaseModel):
    name: str | None = None
    adapter_config: dict | None = None
    skills: list[str] | None = None
    status: str | None = None           # "active" | "inactive" | "archived"
    heartbeat_interval_seconds: int | None = None

class AgentResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    slug: str
    dir_path: str
    adapter_type: str
    adapter_config: dict
    skills: list[str]
    status: str
    heartbeat_interval_seconds: int
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime

class AgentFileList(BaseModel):
    files: list[str]

class AgentFileContent(BaseModel):
    path: str
    content: str
```

### 3. Service — `services/agent.py`

```python
KNOWN_ADAPTER_TYPES = ["claude_code", "codex", "anthropic_api"]

class AgentService:
    def __init__(self, db: Session, filesystem: FilesystemService): ...

    def create(self, org: Organization, data: AgentCreate) -> Agent:
        # 1. Validate adapter_type in KNOWN_ADAPTER_TYPES → raise 422 if not
        # 2. Generate slug from name (slugify)
        # 3. Call filesystem.scaffold_agent_dir(
        #        org_slug=org.slug,
        #        agent_slug=slug,
        #        base_path=settings.data_dir,
        #        template_name=data.template,
        #        template_vars={
        #            "agent_name": data.name,
        #            "agent_slug": slug,
        #            "org_name": org.name,
        #            "org_slug": org.slug,
        #            "role": data.role or "",
        #            "adapter_type": data.adapter_type,
        #            "gateway_url": settings.gateway_url,
        #            "created_at": utcnow().isoformat(),
        #        },
        #    ) → returns agent_dir (absolute path)
        # 4. Insert Agent row with dir_path=agent_dir, status="active"
        # Return agent

    def get_by_id(self, org_id: UUID, agent_id: UUID) -> Agent: ...
    def get_by_slug(self, org_id: UUID, slug: str) -> Agent: ...
    def get_by_id_or_slug(self, org_id: UUID, identifier: str) -> Agent:
        # Try UUID parse first; if valid UUID call get_by_id, else get_by_slug

    def list_by_org(
        self, org_id: UUID,
        status: str | None = None,
        adapter_type: str | None = None,
    ) -> list[Agent]: ...

    def update(self, org_id: UUID, agent_id: UUID, data: AgentUpdate) -> Agent:
        # Update DB columns for any non-None field in data
        # Return updated agent

    def archive(self, org_id: UUID, agent_id: UUID) -> Agent:
        # Soft delete: set status = "archived"
        # Files on disk are kept

    def get_agent_files(self, agent: Agent) -> list[str]: ...
    def read_agent_file(self, agent: Agent, path: str) -> str: ...
    def write_agent_file(self, agent: Agent, path: str, content: str) -> None: ...
```

### 4. Dependency Function — `services/__init__.py`

```python
def get_agent_service(
    db: Session = Depends(get_db),
    filesystem: FilesystemService = Depends(get_filesystem_service),
) -> AgentService:
    return AgentService(db, filesystem)
```

### 5. Routes — `api/routes/agent.py`

All routes require auth via `get_current_org`. Pattern from chunk 02:
```python
(org, key) = Depends(get_current_org)
```
Scope enforcement uses `require_scope(key, "agents:read")` or `require_scope(key, "agents:write")`.

```
POST   /api/v1/agents
  Scope: agents:write
  Body:  AgentCreate
  Returns: AgentResponse 201

GET    /api/v1/agents
  Scope: agents:read
  Query: ?status=active&adapter_type=claude_code
  Returns: list[AgentResponse] 200

GET    /api/v1/agents/{agent_id}
  Scope: agents:read
  Path:  agent_id = UUID or slug
  Returns: AgentResponse 200

PATCH  /api/v1/agents/{agent_id}
  Scope: agents:write
  Body:  AgentUpdate
  Returns: AgentResponse 200

DELETE /api/v1/agents/{agent_id}
  Scope: agents:write
  Action: soft-delete (archive)
  Returns: AgentResponse 200

GET    /api/v1/agents/{agent_id}/files
  Scope: agents:read
  Returns: AgentFileList 200

GET    /api/v1/agents/{agent_id}/files/{path:path}
  Scope: agents:read
  Returns: AgentFileContent 200

PUT    /api/v1/agents/{agent_id}/files/{path:path}
  Scope: agents:write
  Body:  AgentFileContent
  Returns: 204
```

### 6. Register Router

Add `agent_router` to `api/routes/__init__.py` and include in `main.py`.

## Config

No new environment variables. This chunk consumes:
- `DATA_DIR` — agent filesystem root (from chunk 03)
- `GATEWAY_URL` — injected into template vars (from chunk 03)

## Notes
- Slug is derived from `name` at creation time and is immutable thereafter.
- Agent identification accepts both UUID and slug (`get_by_id_or_slug`).
- File endpoints use `{path:path}` to capture nested paths like `memory/long_term.md`.
- All file operations are scoped to the agent's `dir_path` — path traversal is blocked by `FilesystemService`.
- `adapter_type` is validated against `KNOWN_ADAPTER_TYPES`; unknown values → 422.
- `DELETE` is a soft delete — sets status to `"archived"`, keeps files on disk.

## Change Log

| Date       | Change                                                                                          |
|------------|-------------------------------------------------------------------------------------------------|
| 2026-04-06 | Initial draft                                                                                   |
| 2026-04-06 | Reconciled against chunks 02 and 03: status values corrected (`inactive` replaces `paused`, `error` removed from agent status); added `Referenced By`; added per-route scope annotations; documented `get_current_org` tuple pattern; expanded `create` with full `template_vars` dict; added `KNOWN_ADAPTER_TYPES` constant; added Config section |
| 2026-04-09 | Removed all `gateway.json` references — DB is the single source of truth; no filesystem config file needed |
