# Refactor `server/apps/cli` → Zenve Autonomous CLI

## Context

The current `server/apps/cli` is a **gateway-connected Celery worker**: `zenve login` stores credentials in `~/.zenve/credentials.json`, `zenve daemon start` registers with a gateway and consumes Celery tasks off a per-org Redis queue. The entire design presumes an always-on FastAPI gateway as the source of truth.

`ZENVE_CLI_ARCHITECTURE.md` redefines the CLI as a **completely different product**: a standalone runtime that lives inside a user's GitHub repo, uses a `.zenve/` folder for state, drives a label-based pipeline of agents against a GitHub snapshot, and commits memory + run results back to the repo. No daemon, no gateway, no database.

Per the user's instructions:
- **The API app (`server/apps/api`) stays as-is** — only `server/apps/cli` is refactored.
- **The CLI never scaffolds agents.** It assumes `.zenve/settings.json` and `.zenve/agents/*` already exist in the target repo, authored by the user. There is no `zenve init` command.
- The old `login` / `daemon` commands are deleted outright — no migration shim.
- CLI stays in the monorepo as a uv workspace member, reusing `zenve-adapters` and `zenve-models`.

---

## What is being replaced (full removal)

Everything under `server/apps/cli/src/zenve_cli/` is tied to the old gateway model and gets deleted:

- `cli.py` — `login` / `daemon start|stop|status` commands
- `worker.py` — Celery task, redis pub/sub event publisher
- `gateway_client.py` — HTTP client to FastAPI gateway `/worker/*` routes
- `credentials.py` — `~/.zenve/credentials.json` reader/writer
- `runtime_detect.py` — worker capability advertising (the new per-agent model lives in `.zenve/agents/{name}/settings.json`)

`pyproject.toml` drops `celery[redis]`, `redis`, and gains `pydantic>=2`.

---

## What is being reused

- **`zenve-adapters`** (`server/packages/adapters/`) — `BaseAdapter`, `AdapterRegistry`, `ClaudeCodeAdapter`, `OpenCodeAdapter`. These only spawn subprocess CLIs; `RunContext.gateway_url` / `agent_token` tolerate empty strings in offline mode. Reused via uv workspace.
- **`zenve-models.adapter`** (`server/packages/models/src/zenve_models/adapter.py`) — `RunContext`, adapter config models (`ClaudeCodeConfig`, `OpenCodeConfig`, …). Same workspace.

**Not reused:** `zenve-scaffolding` — the new CLI does not create agent directories, so templates / `ScaffoldingService` are unneeded.

---

## Target structure

```
server/apps/cli/
  pyproject.toml                       ← rewired deps
  src/zenve_cli/
    __init__.py
    cli.py                             ← typer app, wires subcommands
    commands/
      start.py                         ← zenve start [--agent X] [--dry-run]
      snapshot.py                      ← zenve snapshot
      pipeline.py                      ← zenve pipeline
      status.py                        ← zenve status
      agent.py                         ← zenve agent list|logs|enable|disable
    core/
      env.py                           ← load + validate env vars
      config.py                        ← load .zenve/settings.json
      discovery.py                     ← scan .zenve/agents/*
      pipeline.py                      ← label → next-label lookup, cycle / orphan detection
    github/
      client.py                        ← thin httpx wrapper (~8 endpoints)
      snapshot.py                      ← fetch issues/PRs/branches → .zenve/snapshot.json
      labels.py                        ← add/remove label, claim item (assign bot + in-progress)
    runtime/
      executor.py                      ← per-agent: filter → claim → invoke adapter → write run result → label transition
      parallel.py                      ← asyncio.gather over all enabled agents
      commit.py                        ← git add memory/ runs/; commit [zenve]; push
    events/
      emitter.py                       ← emit() → local log file + optional webhook (HMAC-signed)
      types.py                         ← event type string constants
    models/
      settings.py                      ← Pydantic: .zenve/settings.json + per-agent settings.json
      snapshot.py                      ← Pydantic: snapshot.json shape
      run_result.py                    ← Pydantic: runs/{run_id}.json shape
```

Explicit files deleted: `worker.py`, `gateway_client.py`, `credentials.py`, `runtime_detect.py`. No `init` command, no `scaffolding/` module, no templates.

---

## Execution model — `zenve start`

1. **Validate env** (`core/env.py`) — require `GITHUB_TOKEN`, `ZENVE_RUN_ID`, `ZENVE_REPO_URL`, `ANTHROPIC_API_KEY`; optional `ZENVE_WEBHOOK_URL` / `ZENVE_WEBHOOK_SECRET`.
2. **Load config** (`core/config.py`, `core/discovery.py`) — parse `.zenve/settings.json`; scan `.zenve/agents/*`; skip `enabled: false`. Error if `.zenve/` is missing (user-configured, not scaffolded by us).
3. **Snapshot** (`github/snapshot.py`) — one-shot fetch → `.zenve/snapshot.json`. Emit `snapshot.fetched`.
4. **Parallel agents** (`runtime/parallel.py`) — `asyncio.gather` per enabled agent:
   - Filter snapshot by `github_label` + `picks_up` (`issues` / `pull_requests` / `both` / `none`).
   - Empty → emit `agent.nothing_to_do`, return.
   - Claim oldest unclaimed item (`github/labels.py`): assign `zenve-bot` + add `in-progress` label. Skip if claim fails.
   - Build `RunContext` (gateway fields empty); invoke `AdapterRegistry.get(adapter_type).execute(ctx)`.
   - Write `.zenve/agents/{name}/runs/{run_id}.json`.
   - Post-exit label transition via `core/pipeline.py`: remove `in-progress` + current `zenve:*`, add next (or nothing if `null`).
   - Emit `agent.completed` + `pipeline.transition` / `pipeline.end`.
5. **Commit back** (`runtime/commit.py`) — `git add .zenve/agents/*/memory/ .zenve/agents/*/runs/`; commit with `[zenve]` prefix; push. Never commit `.zenve/snapshot.json`.
6. Emit `run.completed`.

`--dry-run`: skip claim, adapter execution, label writes, and commit — just print the filtered plan per agent.

`--agent X`: run only agent `X`; all other stages unchanged.

---

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| CLI location | Stay in monorepo (`server/apps/cli`) as uv workspace member | Share `zenve-adapters` without vendoring; same dev loop. |
| No scaffolding | CLI assumes `.zenve/` is user-authored; error if missing | Per user decision — the CLI runs what it finds, it doesn't create. |
| Old commands | Delete `login` / `daemon` outright | Old and new CLI are different products; half-migrated state is worse than a clean break. API `/worker/*` routes survive untouched. |
| Git ops | Shell out to `git` via `subprocess` | `gitpython` is heavy for ~3 commands. |
| GitHub client | Hand-rolled `httpx` wrapper | We only need issues-list, PRs-list, branches-list, add-label, remove-label, add-assignee. |
| Adapter reuse | Via `zenve-adapters` workspace dep | `RunContext.gateway_url` / `agent_token` default to `""` for local mode — adapters tolerate this. |
| Parallelism | `asyncio.gather` over per-agent coroutines | Matches existing `asyncio.run(adapter.execute(ctx))` pattern. |
| Event webhook | `hmac.new(secret, body, sha256)` → `X-Zenve-Signature` header | Matches spec. |
| Pipeline config home | `.zenve/settings.json` `pipeline` map | Spec. |

---

## Critical files

**Modified**
- `server/apps/cli/pyproject.toml` — remove `celery[redis]`, `redis`; add `pydantic>=2`; keep workspace deps `zenve-adapters`, `zenve-models`.
- `server/apps/cli/src/zenve_cli/cli.py` — shrink to a command registrar.
- `server/justfile` — adjust the `cli` recipe if it referenced the daemon (verify and update).

**Deleted**
- `server/apps/cli/src/zenve_cli/{worker,gateway_client,credentials,runtime_detect}.py`

**New** — everything under the target tree above.

**Untouched** (explicit)
- `server/apps/api/**` — per user instruction
- `server/packages/**` — read-only dependencies

---

## Build order

Staged so each step is testable standalone:

1. **`zenve snapshot`** — env validation + GitHub client + snapshot writer. Runnable against any repo with a PAT.
2. **`zenve pipeline`** — load + validate pipeline (unknown label refs, null terminations, cycle warnings); pretty-print.
3. **`zenve status`** / **`zenve agent list|logs|enable|disable`** — read-only commands over `.zenve/` state.
4. **`zenve start --dry-run`** — discover, filter per agent, print plan. No network writes, no adapter invocation.
5. **`zenve start`** — full run: parallel agents → claim → adapter → label transitions → commit-back + push.
6. **Events** — `emit()` wired into every stage; local file first, webhook HMAC second.

---

## Verification

**Unit**
- Mock GitHub via `httpx.MockTransport`: snapshot parse, label transitions, filter logic (`picks_up` variants).
- Pipeline validator: detects unknown label refs, null terminations, reports cycles.
- Event emitter: local file write + webhook HMAC signature matches spec header format.
- Discovery: respects `enabled: false`, skips non-agent folders.

**Integration**
- Hand-author a minimal `.zenve/` in a throwaway repo (settings + one agent dir with SOUL/AGENTS/HEARTBEAT + `settings.json`).
- `zenve snapshot` with a real PAT; assert `snapshot.json` shape against spec sample.
- `zenve start --dry-run` with a seeded issue labeled `zenve:dev`; assert printed plan lists that issue under the dev agent.
- `zenve start` end-to-end: open issue with `zenve:dev`, confirm: snapshot written, dev agent invoked (real Claude Code), label transitions to `zenve:reviewer`, `runs/{run_id}.json` committed + pushed. Webhook (if set) receives signed events.

**Manual**
- Run with no `~/.zenve/` state, only env vars — confirms the gateway/credentials layer is truly gone.
- Run against a repo with no `.zenve/` — confirms the CLI errors with a clear "missing `.zenve/` — author it first" message rather than offering to scaffold.

---

## Open questions (non-blocking)

1. **Webhook delivery** — sync (block until POST returns) or fire-and-forget? Spec is silent. Plan assumes fire-and-forget with one 1 s retry on failure.
2. **Bot identity for work claiming** — architecture mentions a `zenve-bot` GitHub user. Is there already a PAT/app set up for this, or will the CLI assume the caller's own user account for assignment? Plan assumes whatever user is behind `GITHUB_TOKEN` — simplest, and re-assign-on-claim still prevents double-pickup.
3. **Commit author** — should commits use `git` defaults, or force a Zenve-branded author (`zenve-bot <bot@zenve.dev>`) via `-c user.name=... -c user.email=...`? Plan uses `git` defaults unless specified.
