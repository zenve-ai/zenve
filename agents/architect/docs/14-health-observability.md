# Chunk 14 — Health & Observability

## Goal
Implement health check endpoints for the gateway, database, Redis, Celery workers, and scheduler.

## Depends On
- Chunk 07 (Celery — worker health)
- Chunk 10 (Heartbeat Scheduler — scheduler status)

## Deliverables

### 1. Pydantic Models — `models/health.py`

```python
class HealthResponse(BaseModel):
    status: str                         # healthy, degraded, unhealthy
    version: str
    uptime_seconds: float
    checks: dict[str, HealthCheck]

class HealthCheck(BaseModel):
    status: str                         # ok, error
    latency_ms: float | None = None
    message: str | None = None

class WorkerStatus(BaseModel):
    name: str
    status: str
    active_tasks: int
    processed: int
    uptime_seconds: float | None
```

### 2. Health Service — `services/health.py`

```python
class HealthService:
    def __init__(self, db: Session, redis, scheduler, adapter_registry): ...

    async def check_all(self) -> HealthResponse:
        checks = {}

        # Database
        checks["database"] = await self._check_db()

        # Redis
        checks["redis"] = await self._check_redis()

        # Scheduler
        checks["scheduler"] = self._check_scheduler()

        # Adapters
        checks["adapters"] = await self._check_adapters()

        overall = "healthy" if all(c.status == "ok" for c in checks.values()) else "degraded"
        return HealthResponse(status=overall, version=VERSION, uptime_seconds=..., checks=checks)

    async def get_worker_status(self) -> list[WorkerStatus]:
        """Query Celery inspect for active workers."""
        inspect = celery.control.inspect()
        active = inspect.active()
        stats = inspect.stats()
        # Build WorkerStatus for each worker
        ...
```

### 3. Routes — `api/routes/health.py`

```
GET    /api/v1/health                  → gateway health (no auth required)
  Returns: HealthResponse with DB, Redis, scheduler, adapter checks

GET    /api/v1/health/workers          → Celery worker status (auth required)
  Returns: list[WorkerStatus]
```

### 4. Register Router

Add health_router to `api/routes/__init__.py`.

`/health` is unauthenticated (for load balancer probes). `/health/workers` requires auth.

## Notes
- `/health` is the primary endpoint for load balancers and monitoring.
- DB check: simple `SELECT 1` query with timing.
- Redis check: `PING` command with timing.
- Scheduler check: verify APScheduler is running and `heartbeat_tick` job exists.
- Adapter check: call `health_check()` on each registered adapter.
- Worker status uses Celery's `inspect()` API — may timeout if no workers are connected.
- Version string comes from package metadata or a constant.
