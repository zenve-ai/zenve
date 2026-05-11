# Zenve Architecture

## Guiding Principle

**The runtime daemon is the brain. The CLI and React UI are thin frontends.**

All business logic — workspace management, scheduling, run execution, result storage — lives in the runtime daemon. The CLI and web UI are display/control surfaces that communicate with the runtime over HTTP. Neither the CLI nor the UI should own any execution logic.

## Inspiration

This design mirrors the [opencode server model](https://opencode.ai/docs/server): a headless daemon owns all state and exposes an HTTP API; the TUI (and any future client) is just a frontend that connects to it. The CLI auto-starts the server if it is not already running, then connects — users never have to manage the daemon manually.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   zenve runtime                     │
│              (headless daemon :8001)                │
│                                                     │
│  workspaces │ scheduling │ run execution │ results  │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP / SSE
           ┌───────────┴───────────┐
           │                       │
    ┌──────▼──────┐         ┌──────▼──────┐
    │  zenve CLI  │         │  React UI   │
    │  (TUI/term) │         │  (future)   │
    └─────────────┘         └─────────────┘
```

## Component Roles

### `zenve server` — runtime daemon
- Headless process, listens on port **8001**
- Owns the workspace registry (workspaces are registered here, not in flat files)
- Owns scheduling: cron triggers live in the daemon, not in the CLI
- Executes runs: spawns adapters, streams output, persists results
- Exposes REST + SSE endpoints consumed by all frontends

### `zenve` CLI — terminal frontend
- Thin client; delegates all heavy work to the runtime via HTTP
- **Auto-starts the runtime** if `/healthz` returns non-200 (see below)
- Renders a TUI over the SSE event stream from the runtime
- Commands that require runtime: `run`, `status`, `workspace add/ls/remove`
- Commands that work standalone (no runtime needed): `init`, `doctor`, `env`

#### `zenve server` subcommands
| Subcommand | Description |
|------------|-------------|
| `zenve server` | Start the daemon in the **foreground** (Docker / CI / debug) |
| `zenve server stop` | Send SIGTERM to the daemon (via `~/.zenve/runtime.pid` or `lsof` fallback) |
| `zenve server logs` | Print last 50 lines of `~/.zenve/runtime.log` |
| `zenve server logs -f` | Tail `~/.zenve/runtime.log` in real time |

### React UI — web frontend (future)
- Same HTTP API as the CLI
- No special privileges; talks the same endpoints

## Auto-Start Behavior

When the CLI needs the runtime (e.g. `zenve run`):

1. `GET /healthz` on `localhost:8001`
2. If healthy → connect and proceed
3. If down → locate `runtime-start` binary next to the `zenve` executable (same venv/bin)
4. Spawn `runtime-start` as a detached background process (`start_new_session=True`), stdout/stderr → `~/.zenve/runtime.log`
5. Poll `/healthz` up to 10s, then connect and proceed — user sees no manual step

`ensure_runtime()` in `zenve_cli/runtime/client.py` implements this logic and is called at the top of every command that requires the runtime.

`zenve-runtime` is declared as a dependency of `zenve-cli` so `runtime-start` is always installed alongside `zenve` on any machine.

This is the same pattern opencode uses for its server mode.

## Run Execution Flow

```
CLI                          Runtime                      Adapter
 │                              │                             │
 ├─ POST /workspaces/{id}/runs ─▶│                             │
 │                              ├─ spawn adapter ────────────▶│
 │                              │◀─ stdout/stderr events ─────┤
 │◀─ SSE stream ────────────────┤                             │
 │  (render TUI)                ├─ persist result             │
 │                              │                             │
```

1. CLI calls `POST /workspaces/{id}/runs` with run config
2. Runtime executes the run (spawns the configured adapter)
3. Runtime streams events back as SSE
4. CLI TUI consumes the stream and renders output in real time
5. Runtime persists the final result; CLI can later query it

## Scheduling

Scheduling is **owned by the runtime daemon**, not the CLI or TUI.

- Cron triggers are stored and fired by the runtime
- The CLI `status` command reads schedule state from the runtime; it does not drive it
- The current in-process cron loop in the TUI (`tui.py`) is **technical debt** to be migrated

## Runtime Files

The daemon writes to `~/.zenve/` on the host machine:

| File | Written by | Purpose |
|------|-----------|---------|
| `~/.zenve/runtime.pid` | runtime lifespan startup / shutdown | PID for `zenve server stop` |
| `~/.zenve/runtime.log` | runtime `logging.basicConfig` file handler | Persistent log, always written regardless of start method |

## Current Status

### Done
- `/healthz` endpoint on the runtime
- Workspace registry (`GET/POST /workspaces`)
- `POST /workspaces/{id}/runs` route stub
- Run result reading (`GET /workspaces/{id}/runs/{run_id}`)
- CLI workspace commands that talk to the runtime
- **CLI auto-start** via `ensure_runtime()` — `zenve-runtime` is a dependency of `zenve-cli`
- **`zenve server` subcommands** — foreground start, stop, logs, logs -f
- **PID file** written by the runtime lifespan (`~/.zenve/runtime.pid`)
- **Log file** always written by the runtime (`~/.zenve/runtime.log`)

### Missing / Technical Debt
- Runtime actually executing runs (run engine not wired to route)
- SSE streaming from runtime to CLI
- Scheduling moved from TUI cron loop into runtime daemon
- React UI (future work)

## CLI Commands: Runtime Required vs Standalone

| Command | Requires Runtime |
|---------|-----------------|
| `zenve run` | Yes (auto-started) |
| `zenve status` | Yes (auto-started) |
| `zenve workspace add/ls/remove` | Yes (auto-started) |
| `zenve server stop/logs` | No (operates on files/processes) |
| `zenve init` | No |
| `zenve doctor` | No |
| `zenve env` | No |
