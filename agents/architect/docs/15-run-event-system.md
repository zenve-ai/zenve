# Chunk 15 — Run Event System

## Goal
Add structured, append-only run events as a middle observability layer between the runs summary table and raw transcripts on disk. Adapters emit uniform gateway events via an `on_event` callback injected through `RunContext`, enabling live progress tracking and post-mortem timelines without parsing transcripts.

## Depends On
- Chunk 05 — Adapter Interface (RunContext, RunResult, BaseAdapter)
- Chunk 07 — Celery Setup & Run Execution (execute_agent_run task, where lifecycle events are emitted)
- Chunk 08 — Runs CRUD (Run model, RunService, runs table FK)

## Referenced By
- Chunk 06 — Claude Code Adapter (emits execution events via `ctx.on_event`)
- Chunk 14 — Health & Observability (event data feeds status checks)

## Deliverables

### 1. Three-Layer Observability Model

The gateway stores run information at three granularity levels. Each layer serves a different purpose and is derived from the one below it.

```
Transcript (disk)     <-- adapter writes everything, raw
    | adapter parses
Events (DB table)     <-- structured moments extracted from the stream
    | celery task summarizes
Run record (DB table) <-- final status, cost, duration
```

| Layer | Storage | Purpose | Example Query |
|-------|---------|---------|---------------|
| `runs` table | DB | Summary: status, timestamps, cost | "Show all failed runs this week" |
| `run_events` table | DB | Timeline: ordered structured events | "What tools did the agent call?" |
| Transcript on disk | Filesystem | Raw truth: complete output | "Why did line 847 happen?" |

**Decoupling property:** if events fail to write, the transcript still has everything. Events can always be rebuilt by reparsing a transcript.

### 2. Event Schema — `models/run_event.py`

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class RunEventType(str, Enum):
    # Lifecycle events -- emitted by the Celery task, same for all adapters
    QUEUED = "queued"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

    # Execution events -- emitted by adapters, mapped from runtime output
    OUTPUT = "output"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    USAGE = "usage"

class RunEventResponse(BaseModel):
    id: UUID
    run_id: UUID
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
    on_event: OnEventCallback   # injected by the Celery task, called by adapters
```

### 6. RunContext Builder Update — `services/run_context.py`

`build_run_context()` gains an `on_event` parameter:

```python
def build_run_context(
    agent: Agent,
    run: Run,
    adapter_registry: AdapterRegistry,
    on_event: OnEventCallback,
    message: str | None = None,
) -> RunContext:
    # ... existing logic from Chunk 05 ...
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
        run_id: UUID,
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
        run_id: UUID,
        after: UUID | None = None,
        limit: int = 100,
    ) -> list[RunEvent]:
        """Return events for a run, ordered by created_at.
        If `after` is provided, return only events created after that event ID (cursor pagination).
        """
        query = self.db.query(RunEvent).filter(RunEvent.run_id == run_id)
        if after:
            cursor_event = self.db.query(RunEvent).get(after)
            if cursor_event:
                query = query.filter(RunEvent.created_at > cursor_event.created_at)
        return query.order_by(RunEvent.created_at).limit(limit).all()
```

### 8. Dependency Function — `services/__init__.py`

```python
def get_run_event_service(db: Session = Depends(get_db)) -> RunEventService:
    return RunEventService(db)
```

### 9. Celery Task Update — `services/tasks.py`

The `execute_agent_run` task builds the `on_event` closure and emits lifecycle events. Adapters only emit execution events.

```python
@celery.task(bind=True, max_retries=2, time_limit=700)
def execute_agent_run(self, run_id: str):
    run = run_service.get(run_id)
    agent = agent_service.get(run.agent_id)
    adapter = adapter_registry.get(agent.adapter_type)

    # Build the on_event closure -- captures run_id so adapters don't pass it
    def on_event(event_type: str, content: str = None, metadata: dict = None):
        run_event_service.create(
            run_id=run_id,
            event_type=event_type,
            content=content,
            metadata=metadata,
        )
        # FUTURE: publish to Redis pub/sub for WebSocket subscribers

    # Lifecycle: STARTED
    on_event("started")
    run_service.update(run_id, status="running", started_at=utcnow())

    try:
        ctx = build_run_context(agent, run, adapter_registry, on_event=on_event)
        result = adapter.execute(ctx)
        transcript_path = write_transcript(agent, run, result)

        if result.exit_code == 0:
            on_event("completed", metadata=result.token_usage)
            final_status = "completed"
        else:
            on_event("failed", content=result.error)
            final_status = "failed"

        run_service.update(run_id,
            status=final_status,
            finished_at=utcnow(),
            exit_code=result.exit_code,
            token_usage=result.token_usage,
            transcript_path=transcript_path,
            error_summary=result.error,
        )

    except TimeoutError:
        on_event("timeout")
        run_service.update(run_id, status="timeout", finished_at=utcnow())
    except Exception as e:
        on_event("failed", content=str(e))
        run_service.update(run_id,
            status="failed",
            finished_at=utcnow(),
            error_summary=str(e),
        )
        raise self.retry(exc=e)
```

**Responsibility split:**
- Celery task emits: `started`, `completed`, `failed`, `timeout`
- Adapters emit: `output`, `tool_call`, `tool_result`, `error`, `usage`

### 10. Claude Code Adapter Update — `agents/claude_code.py`

The adapter switches from `--output-format json` to `--output-format stream-json` and reads stdout line-by-line, translating each Claude Code event into a gateway event via `ctx.on_event`.

**Claude Code `stream-json` event types and their gateway mappings:**

| Claude Code `type` | Gateway `event_type` | What it captures |
|---------------------|----------------------|------------------|
| `system` | `output` | Session initialization, session_id |
| `assistant` | `output` | Model text output |
| `tool_use` | `tool_call` | Tool name, input args, tool_use_id |
| `tool_result` | `tool_result` | Result content, is_error, tool_use_id |
| `result` | `usage` | Token counts, cost |
| `error` | `error` | Non-fatal runtime error |

**Key changes to `execute()`:**

```python
async def execute(self, ctx: RunContext) -> RunResult:
    # ... build prompt and env (unchanged) ...

    # Spawn with stream-json instead of json
    proc = await asyncio.create_subprocess_exec(
        *args,   # args now use --output-format stream-json
        cwd=ctx.agent_dir, env=env,
        stdout=PIPE, stderr=PIPE,
    )

    # Stream stdout line by line
    full_stdout_lines: list[str] = []
    token_usage: dict | None = None

    async for raw_line in proc.stdout:
        line = raw_line.decode().strip()
        if not line:
            continue
        full_stdout_lines.append(line)

        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            ctx.on_event("output", content=line)
            continue

        event_type = parsed.get("type")

        if event_type == "system":
            ctx.on_event("output",
                content=f"Session initialized: {parsed.get('session_id', 'unknown')}",
                metadata={"session_id": parsed.get("session_id")},
            )
        elif event_type == "assistant":
            text = parsed.get("message", {}).get("content", "")
            if isinstance(text, list):
                text = "".join(
                    b.get("text", "") for b in text if b.get("type") == "text"
                )
            if text:
                ctx.on_event("output", content=text)
        elif event_type == "tool_use":
            ctx.on_event("tool_call",
                content=f"Calling tool: {parsed.get('name', 'unknown')}",
                metadata={
                    "tool": parsed.get("name"),
                    "tool_use_id": parsed.get("id"),
                    "input": parsed.get("input", {}),
                },
            )
        elif event_type == "tool_result":
            result_content = str(parsed.get("content", ""))
            summary = result_content[:500] + "..." if len(result_content) > 500 else result_content
            ctx.on_event("tool_result",
                content=summary,
                metadata={
                    "tool_use_id": parsed.get("tool_use_id"),
                    "is_error": parsed.get("is_error", False),
                    "full_result": parsed.get("content", ""),
                },
            )
        elif event_type == "result":
            usage = parsed.get("usage", {})
            if usage:
                token_usage = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                    "cost_usd": parsed.get("total_cost_usd"),
                }
                ctx.on_event("usage", metadata=token_usage)
        elif event_type == "error":
            ctx.on_event("error",
                content=parsed.get("message", "unknown error"),
                metadata=parsed,
            )
        # Unknown types ignored -- forward compatibility

    stderr_bytes = await proc.stderr.read() if proc.stderr else b""
    await proc.wait()
    duration = monotonic() - start_time

    return RunResult(
        exit_code=proc.returncode or 0,
        stdout="\n".join(full_stdout_lines),
        stderr=stderr_bytes.decode(),
        token_usage=token_usage,
        duration_seconds=duration,
        error=stderr_bytes.decode() if proc.returncode != 0 else None,
    )
```

**CLI args change:** `_build_cli_args` now emits `--output-format stream-json` instead of `--output-format json`.

### 11. Routes — `api/routes/run_event.py`

```
GET /api/v1/runs/{run_id}/events    -> list run events (timeline)
  Query: ?after=<event_id>&limit=100
  - Cursor pagination: `after` is the last event ID the client saw
  - Returns events ordered by created_at ascending
  - Clients poll every 1-2s with ?after=<last_seen_id> for live feed
  - Polling stops when run reaches terminal state (completed, failed, timeout)
  Response: list[RunEventResponse]
```

This endpoint is added alongside existing run routes (Chunk 08), not as a separate router.

### 12. Example Event Stream

For a run where the agent reads a file and replies:

```json
[
  {"event_type": "started",     "content": null,                                       "metadata": null},
  {"event_type": "output",      "content": "Session initialized: sess_abc123",         "metadata": {"session_id": "sess_abc123"}},
  {"event_type": "output",      "content": "I'll start by reading the auth module.",  "metadata": null},
  {"event_type": "tool_call",   "content": "Calling tool: read_file",                 "metadata": {"tool": "read_file", "input": {"path": "src/auth.py"}}},
  {"event_type": "tool_result", "content": "def authenticate(user): ...",             "metadata": {"is_error": false, "full_result": "..."}},
  {"event_type": "output",      "content": "Found 3 issues in the auth module:",     "metadata": null},
  {"event_type": "usage",       "content": null,                                       "metadata": {"input_tokens": 1200, "output_tokens": 340, "cost_usd": 0.012}},
  {"event_type": "completed",   "content": null,                                       "metadata": {"input_tokens": 1200, "output_tokens": 340}}
]
```

## Config
No new environment variables. The `run_events` table uses the existing database connection.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Event storage | DB table, not in-memory | Survives worker restarts; supports REST polling and backfill |
| Callback injection | Closure in Celery task, injected via RunContext | Adapters stay decoupled from persistence layer |
| Lifecycle vs execution split | Celery task owns lifecycle, adapters own execution events | Clear responsibility boundary; adapters never need to know about run state machine |
| Claude Code output format | `stream-json` (line-delimited JSON) | Enables real-time event emission as lines arrive |
| Cursor pagination | `?after=<event_id>` | Simple, stateless; clients only need to track last seen ID |
| Content truncation | tool_result content capped at 500 chars, full in metadata | Keeps timeline readable; full data available when needed |

## Future

- **WebSocket streaming** — `on_event` closure publishes to Redis pub/sub; a `/ws/runs/{run_id}/events` endpoint subscribes and forwards. No adapter changes needed.
- **Event retention / TTL** — Purge old events after N days; transcript on disk is the permanent record.
- **Transcript reparsing** — Rebuild events from archived transcripts if events are lost or schema changes.
- **SSE endpoint** — Alternative to WebSocket for simpler clients.

## Notes
- `on_event` is the single choke point for all events. Extending delivery (WebSocket, webhooks, SSE) means modifying one closure, not every adapter.
- Adapters are unaware of persistence. They call `ctx.on_event(type, content, metadata)` and move on.
- Unknown Claude Code event types are silently ignored for forward compatibility.
- The `on_event` callback is synchronous by design — DB writes inside a Celery worker are fast and serialization keeps event ordering simple.
- If `on_event` raises, the adapter run is not affected — wrap the closure body in try/except in production to isolate event persistence failures from execution.

## Change Log

| Date       | Change                           |
|------------|----------------------------------|
| 2026-04-08 | Initial creation of chunk 15     |
