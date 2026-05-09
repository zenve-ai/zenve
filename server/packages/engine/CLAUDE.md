# CLAUDE.md — zenve engine

Self-contained library that executes one **run** against a repo with `.zenve/`. The CLI is a thin wrapper over this; the runtime daemon (`apps/runtime`) will call it directly to own run lifecycle.

The engine is the **read+write owner of `.zenve/` at runtime**. The CLI's `init` command owns the **write-side at scaffold time**.

## Public API

```python
from zenve_engine import run, snapshot, RunReport, RunResultFile, Snapshot

run(
    project_dir: Path,
    *,
    run_id: str,
    github_token: str,
    repo: str,
    webhook_url: str | None = None,
    webhook_secret: str | None = None,
    only_agent: str | None = None,
    env_vars: dict[str, str] | None = None,
    on_event: Callable[[dict], None] | None = None,
    registry: AdapterRegistry | None = None,
) -> RunReport

snapshot(
    project_dir: Path,
    *,
    run_id: str,
    github_token: str,
    repo: str,
) -> Snapshot
```

`run()` does: **preflight** (clean working tree outside `.zenve/`, clean `.zenve/` unless `auto_commit_zenve=True`, `origin/<default_branch>` exists after fetch) → load settings → discover agents → snapshot GitHub → reconcile claims → run all agents in parallel → commit `.zenve/agents/` → emit `RUN_COMPLETED`.

Preflight raises `DirtyTreeError` or `MissingRemoteBranchError` from `zenve_engine.errors` before any side effects. Reason the dirty check matters: a successful `artifact_pr` merge runs `git reset --hard origin/<branch>` in the parent repo, which would silently wipe uncommitted work; and `commit_agents` at the end would otherwise bundle unrelated edits into the auto-commit.

`on_event` lets the daemon stream events live (in-process pub/sub). It's additive — the file log at `.zenve/events.log` and the optional webhook always run.

## External contract

| Dep | Why |
|---|---|
| `git` CLI on PATH | worktree create/remove, commit, push, fetch |
| `gh` CLI on PATH | PR create/merge in `artifact_pr` / `code_pr` / `review_pr` modes |
| `httpx` + `GITHUB_TOKEN` | snapshot reads + label transitions via REST |
| `zenve_adapters` | `AdapterRegistry`, `BaseAdapter` — actual subprocess that runs an agent |
| `zenve_models` | `RunContext`, `RunResult` — adapter input/output shape |

## Structure

```
src/zenve_engine/
├── __init__.py            # exports run, snapshot, RunReport, RunResultFile, Snapshot
├── api.py                 # the public run() / snapshot() entry points
├── constants.py           # paths, label names, GitHub API config
├── env.py                 # token resolution, run_id, dotenv loading
├── config.py              # load_project_settings() → ProjectSettings
├── discovery.py           # discover_agents() → list[DiscoveredAgent]
├── pipeline.py            # next_label / prev_labels / validate_pipeline
├── claims.py              # local claims.json — add/remove/expired
├── models/                # Pydantic models — settings, snapshot, run_result, claims
├── events/                # EventEmitter (file log + webhook) + event type constants
├── github/                # httpx-based GitHub REST client + label/snapshot helpers
├── git/                   # subprocess git wrappers + worktree helpers
└── exec/                  # executor (single-agent flow) + parallel (asyncio.gather)
```

## Rules

- **Engine never imports from `zenve_cli`.** Direction is one-way: CLI → engine.
- **Engine has no presentation concerns.** No rich/typer/questionary. Output is via `on_event`, return values, and the events log.
- **No `HTTPException`.** Engine raises plain Python exceptions; callers translate.
- **Filesystem layout under `.zenve/` is the contract** with the daemon. The daemon reads what the engine writes — don't change shapes without updating `apps/runtime/CLAUDE.md`.
