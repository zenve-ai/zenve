# Plan: Session Resumption for Runs (Backend)

## Context

Each run currently spawns a fresh CLI session. The adapter captures `session_id` from the first event but discards it. We need to:
1. Store `session_id` on runs so the frontend can group runs by session
2. Accept `session_id` on run creation so a new run can resume an existing CLI session
3. Pass the right CLI flag (`--resume` for Claude Code, `--session` for OpenCode)
4. Expose a sessions endpoint that returns sessions with nested runs

No separate Session table — `session_id` is a grouping key on `Run`.

## Changes

### 1. Data models — `packages/models/src/zenve_models/adapter.py`
- Add `session_id: str | None = None` to `RunContext`
- Add `session_id: str | None = None` to `RunResult`

### 2. Pydantic schemas — `packages/models/src/zenve_models/run.py`
- Add `session_id: str | None = None` to `RunCreate`
- Add `session_id: str | None` to `RunResponse`
- Add new `SessionResponse` model:
  ```python
  class SessionResponse(BaseModel):
      session_id: str
      agent_id: str
      agent_slug: str
      runs: list[RunResponse]
  ```

### 3. ORM model — `packages/db/src/zenve_db/models.py`
- Add `session_id: Mapped[str | None] = mapped_column(String(256), nullable=True)` to `Run`

### 4. RunService — `packages/services/src/zenve_services/run.py`
- Add `session_id` param to `create_run()`, pass to `Run()`
- Add `session_id` filter to `list_runs()`
- Add `list_sessions(org_id, agent_id=None, limit=50)` method:
  - Query runs WHERE session_id IS NOT NULL, group by session_id
  - Return grouped data for the route to assemble into `SessionResponse`

### 5. build_run_context — `packages/services/src/zenve_services/run_context.py`
- Add `session_id` param, pass to `RunContext()`

### 6. Routes — `apps/api/src/api/routes/run.py`
- Pass `body.session_id` to `create_run()` and `build_run_context()`
- Add `session_id` query param to `list_runs` endpoint
- Add new `GET /api/v1/orgs/{org_id}/sessions` endpoint with optional `agent_id` filter
  - Returns `list[SessionResponse]` with nested runs

### 7. ClaudeCodeAdapter — `packages/adapters/src/zenve_adapters/claude_code.py`
- `build_cli_args`: add `session_id` param; when set, append `--resume <session_id>`
- `execute`: pass `ctx.session_id` to `build_cli_args`; capture session_id from system event; return in `RunResult`

### 8. OpenCodeAdapter — `packages/adapters/src/zenve_adapters/open_code.py`
- `build_cli_args`: add `session_id` param; when set, append `--session <session_id>`
- `execute`: init local `session_id` from `ctx.session_id`; return in `RunResult`

### 9. execute_run — `packages/services/src/zenve_services/run_executor.py`
- After `adapter.execute()`, persist `result.session_id` on the `Run` record
- Include `session_id` in transcript JSON

### 10. Tests
- `test_claude_code_adapter.py`: test `--resume` in args; test session_id in RunResult
- `test_open_code_adapter.py`: test `--session` in args; test session_id in RunResult

## Files touched (11, no new files)

| File | Change |
|------|--------|
| `packages/models/src/zenve_models/adapter.py` | `session_id` on RunContext + RunResult |
| `packages/models/src/zenve_models/run.py` | `session_id` on RunCreate + RunResponse + new SessionResponse |
| `packages/db/src/zenve_db/models.py` | `session_id` column on Run |
| `packages/services/src/zenve_services/run.py` | `create_run` + `list_runs` + `list_sessions` |
| `packages/services/src/zenve_services/run_context.py` | `session_id` param |
| `packages/services/src/zenve_services/run_executor.py` | persist session_id + transcript |
| `apps/api/src/api/routes/run.py` | thread session_id + list filter + sessions endpoint |
| `packages/adapters/src/zenve_adapters/claude_code.py` | `--resume` flag + capture |
| `packages/adapters/src/zenve_adapters/open_code.py` | `--session` flag + capture |
| `packages/adapters/tests/test_claude_code_adapter.py` | session_id tests |
| `packages/adapters/tests/test_open_code_adapter.py` | session_id tests |

## Verification

1. `cd server && uv run pytest packages/adapters/tests/ -v`
2. `just dev` → trigger a run → confirm `session_id` in response
3. Trigger a second run with that `session_id` → confirm `--resume` in CLI args
4. `GET /runs?session_id=X` → confirm filtering works
5. `GET /sessions?agent_id=X` → confirm sessions with nested runs
