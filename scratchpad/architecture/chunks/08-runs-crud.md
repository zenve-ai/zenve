# Chunk 08 — Runs CRUD

## Goal
Implement the Run entity: ORM model, service, REST routes for triggering, listing, and reading runs.

## Depends On
- Chunk 07 (Celery — runs are dispatched as Celery tasks)

## Deliverables

### 1. ORM Model — `db/models.py`

Add `Run` table:

```
runs
  id              UUID PK
  org_id          UUID FK → organizations
  agent_id        UUID FK → agents
  trigger         VARCHAR NOT NULL      -- heartbeat, manual, webhook, collaboration
  status          VARCHAR NOT NULL      -- queued, running, completed, failed, timeout
  adapter_type    VARCHAR NOT NULL
  message         TEXT NULL             -- the input message (for manual runs)
  started_at      TIMESTAMP NULL
  finished_at     TIMESTAMP NULL
  exit_code       INT NULL
  error_summary   TEXT NULL
  token_usage     JSON NULL             -- {input_tokens, output_tokens, cache_read, cost_usd}
  transcript_path VARCHAR NULL          -- path to full transcript on disk
  celery_task_id  VARCHAR NULL          -- for task tracking/revocation
  collaboration_id UUID FK NULL         -- set for collaboration sub-runs (Chunk 11)
  created_at      TIMESTAMP
```

Relationships: `Agent.runs`, `Organization.runs`.

### 2. Pydantic Models — `models/run.py`

```python
class RunCreate(BaseModel):
    agent_id: UUID
    message: str | None = None
    params: dict | None = None          # future: extra params for adapter

class RunResponse(BaseModel):
    id: UUID
    org_id: UUID
    agent_id: UUID
    trigger: str
    status: str
    adapter_type: str
    message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    exit_code: int | None
    error_summary: str | None
    token_usage: dict | None
    celery_task_id: str | None
    collaboration_id: UUID | None
    created_at: datetime

class RunTranscript(BaseModel):
    run_id: UUID
    content: str
```

### 3. Service — `services/run.py`

```python
class RunService:
    def __init__(self, db: Session): ...

    def create_run(
        self,
        org_id: UUID,
        agent_id: UUID,
        trigger: str,
        adapter_type: str,
        message: str | None = None,
        status: str = "queued",
        collaboration_id: UUID | None = None,
    ) -> Run: ...

    def get_by_id(self, org_id: UUID, run_id: UUID) -> Run: ...

    def list_runs(
        self,
        org_id: UUID,
        agent_id: UUID | None = None,
        status: str | None = None,
        trigger: str | None = None,
        limit: int = 50,
    ) -> list[Run]: ...

    def update(self, run_id: UUID, **kwargs) -> Run: ...

    def get_transcript(self, run: Run) -> str | None:
        """Read transcript from disk using run.transcript_path."""

    def has_active_run(self, agent_id: UUID) -> bool:
        """Check if agent has a run in 'queued' or 'running' status."""

    def cancel_run(self, run: Run) -> Run:
        """Revoke Celery task and mark run as failed."""
```

### 4. Dependency Function — `services/__init__.py`

```python
def get_run_service(db: Session = Depends(get_db)) -> RunService:
    return RunService(db)
```

### 5. Routes — `api/routes/run.py`

```
POST   /api/v1/runs                    → trigger a manual run
  Body: { agent_id, message?, params? }
  - Validates agent exists and belongs to current org
  - Creates run record (status: queued)
  - Dispatches execute_agent_run.delay()
  - Returns RunResponse with celery_task_id

GET    /api/v1/runs                    → list runs
  Query: ?agent_id=...&status=...&trigger=heartbeat&limit=50

GET    /api/v1/runs/{run_id}           → get run details

GET    /api/v1/runs/{run_id}/transcript → get full transcript
  - Reads from disk via run.transcript_path
  - Returns 404 if no transcript yet

DELETE /api/v1/runs/{run_id}/cancel    → cancel a running task
  - Revokes Celery task
  - Marks run as failed
```

### 6. Register Router

Add run_router to `api/routes/__init__.py`.

## Notes
- `POST /runs` is the primary way to trigger manual agent execution.
- Runs created by heartbeat scheduler (Chunk 10) use `trigger="heartbeat"`.
- Runs created by collaborations (Chunk 12) use `trigger="collaboration"`.
- The `cancel` endpoint uses Celery's `revoke()` with `terminate=True`.
- `has_active_run()` is used by the heartbeat scheduler to avoid double-scheduling.
- Transcript is read from disk, not stored in the database (keeps DB lean).
