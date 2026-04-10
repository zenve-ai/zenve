# Chunk 11 — Collaborations Data Model

## Goal
Implement the ORM models, Pydantic schemas, and service for multi-agent collaborations. No execution logic yet — just the data layer and basic CRUD.

## Depends On
- Chunk 08 (Runs — collaborations create sub-runs)

## Deliverables

### 1. ORM Models — `db/models.py`

Add three tables:

```
collaborations
  id              UUID PK
  org_id          UUID FK → organizations
  lead_agent_id   UUID FK → agents
  source_run_id   UUID FK → runs NULL     -- the original run that spawned this
  title           VARCHAR NOT NULL
  status          VARCHAR NOT NULL         -- active, resolved, max_rounds_reached, failed, cancelled
  max_rounds      INT DEFAULT 10
  routing_strategy VARCHAR DEFAULT 'round_robin'
  current_round   INT DEFAULT 0
  resolve_summary TEXT NULL
  celery_task_id  VARCHAR NULL
  created_at      TIMESTAMP
  finished_at     TIMESTAMP NULL

collaboration_members
  id              UUID PK
  collaboration_id UUID FK → collaborations
  agent_id        UUID FK → agents
  role            VARCHAR NOT NULL         -- lead, member
  turn_order      INT NOT NULL             -- 0, 1, 2...
  joined_at       TIMESTAMP

collaboration_messages
  id              UUID PK
  collaboration_id UUID FK → collaborations
  agent_id        UUID FK → agents
  run_id          UUID FK → runs NULL
  round           INT NOT NULL
  content         TEXT NOT NULL
  message_type    VARCHAR NOT NULL         -- contribution, resolve, error
  created_at      TIMESTAMP
```

Relationships:
- `Collaboration.members` → `CollaborationMember`
- `Collaboration.messages` → `CollaborationMessage`
- `Collaboration.lead_agent` → `Agent`

### 2. Pydantic Models — `models/collaboration.py`

```python
class CollaborationCreate(BaseModel):
    agent_ids: list[UUID]               # first is lead
    title: str
    message: str                        # initial message from lead
    max_rounds: int = 10
    routing_strategy: str = "round_robin"

class CollaborationResponse(BaseModel):
    id: UUID
    org_id: UUID
    lead_agent_id: UUID
    title: str
    status: str
    max_rounds: int
    routing_strategy: str
    current_round: int
    resolve_summary: str | None
    created_at: datetime
    finished_at: datetime | None
    members: list[CollaborationMemberResponse]

class CollaborationMemberResponse(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str
    role: str
    turn_order: int

class CollaborationMessageResponse(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str
    round: int
    content: str
    message_type: str
    created_at: datetime
```

### 3. Service — `services/collaboration.py`

```python
class CollaborationService:
    def __init__(self, db: Session): ...

    def create(self, org_id: UUID, data: CollaborationCreate) -> Collaboration:
        # 1. Validate all agent_ids exist and belong to org
        # 2. Create collaboration record
        # 3. Create members (first agent = lead/turn_0, rest = member/turn_N)
        # 4. Save initial message from lead agent
        # 5. Return collaboration

    def get_by_id(self, org_id: UUID, collab_id: UUID) -> Collaboration: ...
    def list_by_org(self, org_id: UUID, status: str | None, agent_id: UUID | None) -> list[Collaboration]: ...

    def get_members_ordered(self, collab_id: UUID) -> list[CollaborationMember]: ...
    def get_messages(self, collab_id: UUID, round: int | None = None, limit: int = 100) -> list[CollaborationMessage]: ...

    def add_message(
        self,
        collaboration_id: UUID,
        agent_id: UUID,
        round: int,
        content: str,
        message_type: str,
        run_id: UUID | None = None,
    ) -> CollaborationMessage: ...

    def update(self, collab_id: UUID, **kwargs) -> Collaboration: ...

    def cancel(self, collab_id: UUID) -> Collaboration:
        # Set status = "cancelled", finished_at = now
```

### 4. Dependency Function — `services/__init__.py`

```python
def get_collaboration_service(db: Session = Depends(get_db)) -> CollaborationService:
    return CollaborationService(db)
```

## Notes
- This chunk is data-only — no Celery task, no execution logic.
- The `routing_strategy` field is stored but only "round_robin" is implemented in Chunk 12.
- `source_run_id` is nullable — collaborations can be created directly via API, not just from a run.
- Members are ordered by `turn_order` for deterministic round-robin.
- Messages have a `message_type` to distinguish contributions from resolve signals and errors.
