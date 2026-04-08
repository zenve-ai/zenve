# Chunk 07 — Celery Setup & Run Execution

## Goal
Set up Celery with Redis broker and implement the `execute_agent_run` task that dispatches agent runs to adapters.

## Depends On
- Chunk 05 (Adapter Interface)
- Chunk 06 (Claude Code Adapter — first adapter to test with)

## Referenced By
- Chunk 08 — Runs CRUD (runs are dispatched as Celery tasks)
- Chunk 15 — Run Event System (task builds on_event closure and emits lifecycle events)

## Deliverables

### 1. Dependencies

Add to project:
- `celery[redis]`
- `redis`

### 2. Celery App — `celery_app.py` (project root level, or `src/zenve/celery_app.py`)

```python
from celery import Celery
from zenve.config import settings

celery = Celery(
    "zenve",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker
)
```

### 3. Config — `config/settings.py`

Add:
```python
REDIS_URL: str = "redis://localhost:6379/0"
RUN_TIMEOUT_SECONDS: int = 600   # default 10 min
```

### 4. Celery Task — `services/tasks.py`

```python
@celery.task(bind=True, max_retries=2, time_limit=700)
def execute_agent_run(self, run_id: str):
    """Execute a single agent run via the appropriate adapter."""

    # 1. Get run + agent from DB
    run = run_service.get(run_id)
    agent = agent_service.get(run.agent_id)

    # 2. Get adapter
    adapter = adapter_registry.get(agent.adapter_type)

    # 3. Mark as running
    run_service.update(run_id, status="running", started_at=utcnow())

    try:
        # 4. Build context
        ctx = build_run_context(agent, run)

        # 5. Execute via adapter
        result = adapter.execute(ctx)

        # 6. Write transcript to disk
        transcript_path = write_transcript(agent, run, result)

        # 7. Update run record
        run_service.update(run_id,
            status="completed" if result.exit_code == 0 else "failed",
            finished_at=utcnow(),
            exit_code=result.exit_code,
            token_usage=result.token_usage,
            transcript_path=transcript_path,
            error_summary=result.error,
        )

    except Exception as e:
        run_service.update(run_id,
            status="failed",
            finished_at=utcnow(),
            error_summary=str(e),
        )
        raise self.retry(exc=e)
```

### 5. Transcript Writer — `services/transcript.py`

```python
def write_transcript(agent: Agent, run: Run, result: RunResult) -> str:
    """Write run transcript to disk. Returns the file path."""
    timestamp = run.started_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}_{str(run.id)[:8]}.md"
    transcript_dir = Path(agent.dir_path) / "runs"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / filename

    content = f"""# Run Transcript
- Run ID: {run.id}
- Agent: {agent.name}
- Trigger: {run.trigger}
- Started: {run.started_at}
- Duration: {result.duration_seconds:.1f}s
- Exit Code: {result.exit_code}

## Output
{result.stdout}

## Errors
{result.stderr if result.stderr else "None"}

## Token Usage
{json.dumps(result.token_usage, indent=2) if result.token_usage else "Not available"}
"""
    transcript_path.write_text(content)
    return str(transcript_path)
```

### 6. DB Session in Celery Tasks

Celery tasks run outside FastAPI's request lifecycle. Need a standalone session factory:

```python
# In services/tasks.py or a shared module
from zenve.db.database import SessionLocal

def get_task_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 7. Development Commands — `justfile`

Add:
```
celery-worker:
    celery -A zenve.celery_app worker --loglevel=info

celery-beat:
    celery -A zenve.celery_app beat --loglevel=info
```

## Notes
- `time_limit=700` on the task = run timeout (600s) + 100s buffer for setup/teardown.
- `worker_prefetch_multiplier=1` ensures workers take one task at a time (agent runs are heavy).
- `task_acks_late=True` means tasks are only acknowledged after completion — prevents losing runs if a worker dies.
- Transcript files are written to `{agent_dir}/runs/` with a timestamp + run ID prefix.
- DB sessions in Celery tasks use `SessionLocal()` directly, not FastAPI's `Depends(get_db)`.
- Redis is used as both broker and result backend. Consider separate Redis DBs for production.
