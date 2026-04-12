# Chunk 15 — Run Event System

## Goal
Add structured, append-only run events as a middle observability layer between the runs summary table and raw transcripts on disk. Adapters emit uniform execution events via an `on_event` callback injected through `RunContext`, enabling live progress tracking and post-mortem timelines without parsing transcripts.

## Depends On
- Chunk 05 — Adapter Interface (RunContext, RunResult, BaseAdapter)
- Chunk 08 — Runs CRUD (Run model, RunService, RunExecutor, runs table FK)

## Referenced By
- Chunk 06 — Claude Code Adapter (emits execution events via `ctx.on_event`)
- Chunk 14 — Health & Observability (event data feeds status checks)

## Deliverables

### 1. Three-Layer Observability Model

The gateway stores run information at three granularity levels. Each layer serves a different purpose.

```
Transcript (disk)     <-- adapter writes everything, raw
    | adapter parses
Events (DB table)     <-- structured moments extracted from the stream
    | executor summarizes
Run record (DB table) <-- final status, cost, duration
```

| Layer | Storage | Purpose | Example Query |
|-------|---------|---------|---------------|
| `runs` table | DB | Summary: status, timestamps, cost | "Show all failed runs this week" |
| `run_events` table | DB | Timeline: ordered execution events | "What tools did the agent call?" |
| Transcript on disk | Filesystem | Raw truth: complete output | "Why did line 847 happen?" |

**Responsibility split:**
- Run lifecycle (`started`, `running`, `completed`, `failed`) — tracked on the `Run` record (`status`, `started_at`, `finished_at`, `error_summary`). Not duplicated into events.
- Execution events — what the agent *did* during the run. Only adapters emit these.

**Decoupling property:** if events fail to write, the transcript still has everything. Events can always be rebuilt by reparsing a transcript.

### 2. Event Schema — `models/run_event.py`

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class RunEventType(str, Enum):
    # Execution events -- emitted by adapters, mapped from runtime output
    OUTPUT = "output"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    USAGE = "usage"

class RunEventResponse(BaseModel):
    id: str
    run_id: str
    event_type: str
    content: str | None
    metadata: dict | None
    created_at: datetime
```

### 3. ORM Model — `db/models.py`

Add `RunEvent` table:

```
run_events
  id          UUID PK
  run_id      UUID FK -> runs (NOT NULL)
  event_type  VARCHAR NOT NULL        -- one of RunEventType values
  content     TEXT NULL               -- human-readable summary
  metadata    JSONB NULL              -- structured data (tool args, token counts, etc.)
  created_at  TIMESTAMP NOT NULL
```

**Indexes:** composite index on `(run_id, created_at)` for efficient timeline queries.

**Constraints:** append-only by convention (no UPDATE/DELETE in service layer).

Relationship: `Run.events` (one-to-many, ordered by `created_at`).

### 4. Callback Type — added to `models/adapter.py`

```python
from typing import Callable

OnEventCallback = Callable[[str, str | None, dict | None], None]
```

### 5. RunContext Update — `models/adapter.py`

Add `on_event` field to the existing `RunContext` dataclass:

```python
@dataclass
class RunContext:
    # ... existing fields from Chunk 05 ...
    on_event: OnEventCallback   # injected by the executor, called by adapters
```

### 6. RunExecutor Update — `services/run_executor.py`

`RunExecutor.build_context()` gains an `on_event` parameter:

```python
def build_context(
    self,
    agent: Agent,
    run_id: str,
    on_event: OnEventCallback,
    message: str | None = None,
    ...
) -> RunContext:
    return RunContext(
        # ... existing fields ...
        on_event=on_event,
    )
```

### 7. Service — `services/run_event.py`

```python
class RunEventService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        run_id: str,
        event_type: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> RunEvent:
        """Append an event to the run's timeline."""
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            content=content,
            metadata=metadata,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_by_run(
        self,
        run_id: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[RunEvent]:
        """Return events for a run, ordered by created_at.
        If `after_id` is provided, return only events created after that event (cursor).
        """
        query = self.db.query(RunEvent).filter(RunEvent.run_id == run_id)
        if after_id:
            cursor = self.db.get(RunEvent, after_id)
            if cursor:
                query = query.filter(RunEvent.created_at > cursor.created_at)
        return query.order_by(RunEvent.created_at).limit(limit).all()
```

### 8. Dependency Function — `services/__init__.py`

```python
def get_run_event_service(db: Session = Depends(get_db)) -> RunEventService:
    return RunEventService(db)
```

### 9. RunExecutor Update — `services/run_executor.py`

`RunExecutor.build_context()` gains an `on_event` parameter and passes it into `RunContext`. The `on_event` closure is built in `execute()` before calling `build_context()`, opening its own DB session per call (executor runs outside the request lifecycle).

```python
class RunExecutor:
    def build_context(
        self,
        agent: Agent,
        run_id: str,
        on_event: OnEventCallback,
        message: str | None = None,
        ...
    ) -> RunContext:
        return RunContext(
            # ... existing fields ...
            on_event=on_event,
        )

    async def execute(self, run_id: str, ctx: RunContext) -> None:
        # on_event closure -- captures run_id, opens its own session per call
        def on_event(event_type: str, content: str | None = None, metadata: dict | None = None):
            db = Session()
            try:
                RunEventService(db).create(run_id=run_id, event_type=event_type, content=content, metadata=metadata)
            except Exception:
                logger.exception("Failed to persist run event for run %s", run_id)
            finally:
                db.close()

        ctx.on_event = on_event  # inject before handing ctx to adapter
        ...
```

The route builds context and fires execution:

```python
ctx = run_executor.build_context(agent=agent, run_id=run.id, message=body.message)
asyncio.ensure_future(run_executor.execute(run.id, ctx))
```

**Note:** `on_event` is synchronous by design — DB writes in the executor are fast and synchronous ordering keeps event sequence simple. Failures are logged but never propagate to the adapter.

### 10. Claude Code Adapter — `adapters/claude_code.py`

Already implemented (Chunk 06). The adapter calls `ctx.on_event(type, content, metadata)` for each stream-json line. No changes needed.

**Claude Code `stream-json` event types and their gateway mappings:**

| Claude Code `type` | Gateway `event_type` | What it captures |
|---------------------|----------------------|------------------|
| `system` | `output` | Session initialization, session_id |
| `assistant` (text block) | `output` | Model text output |
| `assistant` (tool_use block) | `tool_call` | Tool name, input args, tool_use_id |
| `user` (tool_result block) | `tool_result` | Result content, is_error, tool_use_id |
| `result` | `usage` | Token counts, cost |
| `error` | `error` | Non-fatal runtime error |

### 11. Routes — `api/routes/run.py`

Added alongside existing run routes:

```
GET /api/v1/orgs/{org_id}/runs/{run_id}/events    -> SSE stream of run events
  Query: ?after=<event_id>
  - SSE endpoint: Content-Type: text/event-stream
  - On connect: replays all existing events from DB (or from `after` cursor if provided)
  - Then polls DB every ~0.5s for new events and streams them as they arrive
  - Closes stream when run reaches a terminal state (completed, failed, cancelled) and no new events remain
  - Reconnection: client passes Last-Event-ID header (standard SSE) or ?after= query param; server resumes from that event
  - Each SSE event: id=<event_id>, data=<RunEventResponse JSON>
  Response: text/event-stream
```

**SSE event format:**

```
id: <event_id>
data: {"id": "...", "run_id": "...", "event_type": "output", "content": "...", "metadata": null, "created_at": "..."}

```

### 12. Example Event Stream

For a run where the agent reads a file and replies:

```json
[
  {"event_type": "output",      "content": "Session initialized: sess_abc123",         "metadata": {"session_id": "sess_abc123"}},
  {"event_type": "output",      "content": "I'll start by reading the auth module.",   "metadata": null},
  {"event_type": "tool_call",   "content": "Calling tool: read_file",                  "metadata": {"tool": "read_file", "input": {"path": "src/auth.py"}}},
  {"event_type": "tool_result", "content": "def authenticate(user): ...",              "metadata": {"is_error": false}},
  {"event_type": "output",      "content": "Found 3 issues in the auth module:",       "metadata": null},
  {"event_type": "usage",       "content": null,                                        "metadata": {"input_tokens": 1200, "output_tokens": 340, "cost_usd": 0.012}}
]
```

## Config
No new environment variables. The `run_events` table uses the existing database connection.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Event storage | DB table, not in-memory | Survives worker restarts; supports replay for late connections |
| Callback injection | Closure built in `RunExecutor.execute()`, injected via RunContext | Adapters stay decoupled from persistence layer |
| Lifecycle events | Not in run_events | `Run.status`, `started_at`, `finished_at` already track this — no duplication |
| Delivery mechanism | SSE with DB polling | No Redis/WebSocket needed; works for current asyncio-based executor |
| Cursor param | `?after=<event_id>` + `Last-Event-ID` header | Standard SSE reconnection pattern; stateless server |
| Replay on connect | Always replay from beginning (or from cursor) | Late connections get full history; no events lost |
| Stream close | Terminal run status + no pending events | Client doesn't need to know when to stop |
| Content truncation | tool_result content capped at 500 chars, full in metadata | Keeps timeline readable; full data available when needed |

## Future

- **Redis pub/sub** — `on_event` closure publishes to Redis channel; SSE endpoint subscribes instead of DB polling. No adapter changes needed, no route changes needed.
- **Event retention / TTL** — Purge old events after N days; transcript on disk is the permanent record.
- **Transcript reparsing** — Rebuild events from archived transcripts if events are lost or schema changes.

## Notes
- `on_event` is the single choke point for all events. Switching from DB polling to Redis pub/sub means modifying one closure and the SSE endpoint only.
- Adapters are unaware of persistence. They call `ctx.on_event(type, content, metadata)` and move on.
- Unknown Claude Code event types are silently ignored for forward compatibility.
- `on_event` is synchronous by design — DB writes inside the async executor are fast and synchronous ordering keeps event sequence simple.
- `on_event` failures are logged but never propagate — event persistence failures must not kill the run.

## Change Log

| Date       | Change                                                                 |
|------------|------------------------------------------------------------------------|
| 2026-04-08 | Initial creation of chunk 15                                           |
| 2026-04-12 | Removed lifecycle events (started/completed/failed/timeout) — lifecycle tracked on Run record only; switched delivery from polling to SSE with ?after cursor and Last-Event-ID replay; updated executor section to asyncio pattern (no Celery); clarified responsibility split |
