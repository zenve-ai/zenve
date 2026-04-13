# Chunk 17 — Org-Level WebSocket

## Goal
Provide a persistent, real-time channel per org so the frontend receives run lifecycle events immediately — no polling required. One WebSocket connection surfaces all activity across all runs for the org: when a run is created, when its status changes, each execution event emitted by the adapter, and when the run finishes.

## Depends On
- Chunk 01 — Organizations CRUD (org model, OrgService, membership)
- Chunk 08 — Runs CRUD (Run model, RunResponse)
- Chunk 15 — Run Event System (RunEvent model, RunEventResponse, on_event callback)

## Referenced By
- Frontend: `useOrgWebSocket` hook consumes the stream and dispatches Redux actions

## Deliverables

### 1. WebSocketManager — `services/ws_manager.py`

In-process connection registry. Keyed by org ID, holds a list of active `WebSocket` connections.

```python
class WebSocketManager:
    _connections: dict[str, list[WebSocket]]

    async def connect(org_id: str, ws: WebSocket) -> None
    def disconnect(org_id: str, ws: WebSocket) -> None
    async def broadcast(org_id: str, message: dict) -> None
        # Sends JSON to every connected client for the org.
        # Silently removes stale connections (already-closed sockets).
```

Single instance created at startup and stored on `app.state.ws_manager`.

### 2. Lifespan — `api/lifespan.py`

```python
app.state.ws_manager = WebSocketManager()
logger.info("WebSocket ready at ws://0.0.0.0:8000/api/v1/orgs/{org_id}/ws")
```

### 3. Dependency Function — `services/__init__.py`

```python
def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager
```

Also injected into `get_run_executor`:

```python
def get_run_executor(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
) -> RunExecutor:
    return RunExecutor(adapter_registry, ws_manager)
```

### 4. WebSocket Endpoint — `api/routes/ws.py`

```
WS /api/v1/orgs/{org_id}/ws?token=<jwt>
```

**Auth:** Browsers cannot set custom headers on WebSocket upgrade requests, so the JWT is passed as a query param instead of `Authorization: Bearer`. The endpoint decodes it with the same `jose.jwt.decode` + `secret_key` as `get_current_user`.

**Flow:**
1. Decode `?token` → extract `user_id`; close with code `4001` on failure
2. Look up user, resolve org by ID or slug, verify membership; close with code `4003` on failure
3. `ws_manager.connect(org.id, ws)` — accept and register
4. Keep-alive loop: `await websocket.receive_text()` (client pings are ignored)
5. `ws_manager.disconnect` in `finally` on `WebSocketDisconnect` or any error

### 5. Broadcast Points

| Where | Message type | Trigger |
|-------|-------------|---------|
| `routes/run.py` — `trigger_run()` | `run.created` | After `create_run()`, before dispatching executor |
| `RunExecutor.execute()` | `run.status_changed` | After `run.status = "running"` commit |
| `RunExecutor.execute()` — `on_event` closure | `run.event` | After each `RunEventService.create()` via `asyncio.ensure_future` |
| `RunExecutor.execute()` | `run.finished` | After final DB commit (including error path) |

### 6. Message Schema

All messages are JSON objects with `type` and `data` fields:

```json
{"type": "run.created",        "data": {<RunResponse fields>}}
{"type": "run.status_changed", "data": {"run_id": "...", "status": "running", "started_at": "..."}}
{"type": "run.event",          "data": {<RunEventResponse fields>}}
{"type": "run.finished",       "data": {"run_id": "...", "status": "completed|failed|cancelled", "outcome": "...", "finished_at": "..."}}
```

### 7. RunExecutor Changes — `services/run_executor.py`

- Constructor gains `ws_manager: WebSocketManager | None = None`
- `on_event` closure: after DB insert, schedules `asyncio.ensure_future(ws.broadcast(...))` — safe because `on_event` runs inside the async event loop
- `execute()`: awaits `ws.broadcast(run.status_changed)` after status=running commit; awaits `ws.broadcast(run.finished)` after final commit and after the error-handling path

### 8. Frontend — `store/runs/`

**`store/runs/api.ts`** — RTK Query endpoints added:
- `listRuns` — `GET /orgs/{slug}/runs`
- `getRun` — `GET /orgs/{slug}/runs/{id}`
- `getRunEvents` — `GET /orgs/{slug}/runs/{id}/events`

**`store/runs/slice.ts`** — Redux slice holding a live run map updated by WebSocket messages:

```ts
state: {
  runs: Record<string, Run>
  eventsByRunId: Record<string, RunEvent[]>
}

actions: runCreated | runStatusChanged | runEventReceived | runFinished
selectors: selectRuns | selectRunById | selectRunEventsByRunId
```

**`store/index.ts`** — `runs: runsReducer` registered; `runsApi` middleware added.

### 9. Frontend Hook — `hooks/use-org-websocket.ts`

```ts
export function useOrgWebSocket(orgId: string): void
```

- Reads JWT from `token.getToken()`
- Builds `ws(s)://` URL by replacing `http(s)://` in `config.apiUrl`
- Dispatches `runCreated`, `runStatusChanged`, `runEventReceived`, `runFinished` on each message
- Reconnects on close with exponential backoff (base 1s, max 5 retries)
- Cleans up socket and pending retry timer on unmount

## Config
No new environment variables.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| One WS per org | Single endpoint, org-scoped | All runs for an org share one connection; simpler than per-run streams |
| JWT via query param | `?token=<jwt>` | Browsers cannot set `Authorization` headers on WS upgrade requests |
| In-process registry | `WebSocketManager` dict | No Redis needed for the current single-process deployment; can swap later |
| `on_event` async scheduling | `asyncio.ensure_future` | `on_event` is synchronous by design (Chunk 15); `ensure_future` schedules the coroutine onto the running loop without changing the callback signature |
| Broadcast failures | Stale connections silently removed | A closed socket should never break the run; disconnect is a normal condition |
| Frontend reconnect | Exponential backoff, max 5 retries | Handles transient server restarts without hammering; gives up after repeated failure |

## Notes
- `WebSocketManager` is in-memory and per-process. In a multi-process deployment (e.g. multiple uvicorn workers), connections registered in one process will not receive broadcasts from another. A Redis pub/sub layer would be required for that case.
- The `run.event` broadcast uses `asyncio.ensure_future` rather than `await` because `on_event` is a synchronous callback. The future is fire-and-forget; event delivery to WS clients is best-effort and does not affect run execution.
- The SSE endpoint (`GET /runs/{id}/events`) from Chunk 15 remains available for clients that prefer polling or need full replay. The WebSocket delivers the same events in real time but without historical replay on connect.

## Change Log

| Date       | Change |
|------------|--------|
| 2026-04-13 | Initial creation |
