# Chunk 04 — Agents CRUD

## Goal
Implement the Agent entity: ORM model, service, REST routes including file management endpoints.

## Depends On
- Chunk 01 (Organizations)
- Chunk 02 (API Key Auth — routes require auth)
- Chunk 03 (Filesystem & Templates — agent creation scaffolds directory)

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
  adapter_type    VARCHAR NOT NULL       -- "claude_code", "codex", "anthropic_api"
  adapter_config  JSON                   -- adapter-specific settings (model, flags)
  skills          JSON                   -- ["code_review", "testing", "deployment"]
  status          VARCHAR NOT NULL       -- active, paused, error, archived
  heartbeat_interval_seconds  INT DEFAULT 0  -- 0 = disabled
  last_heartbeat_at  TIMESTAMP NULL
  created_at      TIMESTAMP
  updated_at      TIMESTAMP
```

Constraints: `UniqueConstraint("org_id", "name")`, `UniqueConstraint("org_id", "slug")`.
Relationship: `Organization.agents` ↔ `Agent.organization`.

### 2. Pydantic Models — `models/agent.py`

```python
class AgentCreate(BaseModel):
    name: str
    adapter_type: str                    # "claude_code", "codex", "anthropic_api"
    adapter_config: dict = {}
    skills: list[str] = []
    heartbeat_interval_seconds: int = 0
    template: str = "default"           # which template to scaffold from
    role: str | None = None             # passed to template

class AgentUpdate(BaseModel):
    name: str | None = None
    adapter_config: dict | None = None
    skills: list[str] | None = None
    status: str | None = None           # active, paused, archived
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
class AgentService:
    def __init__(self, db: Session, filesystem: FilesystemService): ...

    def create(self, org: Organization, data: AgentCreate) -> Agent:
        # 1. Generate slug from name
        # 2. Scaffold agent directory via FilesystemService
        # 3. Write gateway.json
        # 4. Create DB record
        # Return agent

    def get_by_id(self, org_id: UUID, agent_id: UUID) -> Agent: ...
    def get_by_slug(self, org_id: UUID, slug: str) -> Agent: ...
    def get_by_id_or_slug(self, org_id: UUID, identifier: str) -> Agent:
        # Try UUID first, then slug

    def list_by_org(self, org_id: UUID, status: str | None, adapter_type: str | None) -> list[Agent]: ...

    def update(self, org_id: UUID, agent_id: UUID, data: AgentUpdate) -> Agent:
        # Update DB record
        # Update gateway.json on disk if relevant fields changed

    def archive(self, org_id: UUID, agent_id: UUID) -> Agent:
        # Soft delete: set status = "archived"
        # Keep files on disk

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

All routes require auth via `get_current_org` dependency. Org is resolved from API key.

```
POST   /api/v1/agents                        → create agent
GET    /api/v1/agents                         → list agents
  Query: ?status=active&adapter_type=claude_code
GET    /api/v1/agents/{agent_id}              → get agent (UUID or slug)
PATCH  /api/v1/agents/{agent_id}              → update agent
DELETE /api/v1/agents/{agent_id}              → archive agent (soft delete)

GET    /api/v1/agents/{agent_id}/files        → list files in agent dir
GET    /api/v1/agents/{agent_id}/files/{path:path} → read file
PUT    /api/v1/agents/{agent_id}/files/{path:path} → write/update file
```

### 6. Register Router

Add agent_router to `api/routes/__init__.py`.

## Notes
- Agent identification accepts both UUID and slug (`get_by_id_or_slug`).
- File endpoints use `{path:path}` to capture nested paths like `memory/long_term.md`.
- All file operations are scoped to the agent's `dir_path` — path traversal is blocked by FilesystemService.
- `adapter_type` is validated against known adapter types (for now: hard-coded list; later: AdapterRegistry).
- `DELETE` is a soft delete — sets status to "archived", keeps files.
