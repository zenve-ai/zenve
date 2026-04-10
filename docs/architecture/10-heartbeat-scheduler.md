# Chunk 10 — Heartbeat Scheduler

## Goal
Implement the internal APScheduler that periodically checks which agents are due for a heartbeat and dispatches runs.

## Depends On
- Chunk 08 (Runs — heartbeats create runs)

## Deliverables

### 1. Dependencies

Add to project:
- `apscheduler>=3.10`

### 2. Heartbeat Service — `services/heartbeat.py`

```python
class HeartbeatService:
    def __init__(self, db: Session): ...

    def get_agents_due(self, now: datetime) -> list[Agent]:
        """
        Return agents where:
        - status == 'active'
        - heartbeat_interval_seconds > 0
        - last_heartbeat_at is NULL OR
          now - last_heartbeat_at >= heartbeat_interval_seconds
        """

    def update_last_heartbeat(self, agent_id: UUID, now: datetime) -> None:
        """Update agent.last_heartbeat_at."""

    def get_schedule(self, org_id: UUID) -> list[dict]:
        """
        Return heartbeat schedule for all agents in an org:
        - agent_id, name, interval, last_heartbeat_at, next_due_at
        """
```

### 3. Scheduler Setup — `services/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def heartbeat_tick():
    """Runs every HEARTBEAT_TICK_SECONDS. Checks which agents are due."""
    now = utcnow()
    db = SessionLocal()
    try:
        heartbeat_service = HeartbeatService(db)
        run_service = RunService(db)

        agents = heartbeat_service.get_agents_due(now)

        for agent in agents:
            # Skip if agent already has an active run
            if run_service.has_active_run(agent.id):
                continue

            # Create run record
            run = run_service.create_run(
                org_id=agent.org_id,
                agent_id=agent.id,
                trigger="heartbeat",
                adapter_type=agent.adapter_type,
                status="queued",
            )

            # Dispatch Celery task
            execute_agent_run.delay(run_id=str(run.id))

            # Update last heartbeat timestamp
            heartbeat_service.update_last_heartbeat(agent.id, now)

    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(
        heartbeat_tick,
        "interval",
        seconds=settings.HEARTBEAT_TICK_SECONDS,
        id="heartbeat_tick",
    )
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown(wait=False)
```

### 4. Config — `config/settings.py`

Add:
```python
HEARTBEAT_TICK_SECONDS: int = 30   # how often the scheduler checks
```

### 5. Lifespan Integration — `api/lifespan.py`

Start scheduler on app startup, stop on shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()
```

### 6. Heartbeat Routes — `api/routes/heartbeat.py`

```
GET    /api/v1/heartbeats                      → list heartbeat schedule for all agents in org
POST   /api/v1/heartbeats/{agent_id}/trigger   → force an immediate heartbeat
PATCH  /api/v1/heartbeats/{agent_id}           → update heartbeat interval
  Body: { interval_seconds }
```

### 7. Register Router

Add heartbeat_router to `api/routes/__init__.py`.

## Notes
- The scheduler tick (30s default) is independent of each agent's `heartbeat_interval_seconds`.
- The tick checks: `now - agent.last_heartbeat_at >= agent.heartbeat_interval_seconds`.
- `has_active_run()` prevents double-scheduling if a previous heartbeat run is still active.
- APScheduler runs inside the FastAPI process — no separate process needed.
- `POST /heartbeats/{agent_id}/trigger` creates a manual heartbeat run immediately (bypasses interval check).
- The scheduler uses its own DB session since it runs outside the request lifecycle.
