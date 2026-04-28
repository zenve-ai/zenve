# CLAUDE.md — zenve CLI

Python CLI (`typer`) that runs autonomous agents against a GitHub repo.

## Structure

```
src/zenve_cli/
├── cli.py                  # Typer app + command registration
├── commands/               # One file per CLI command (thin wrappers)
│   ├── start.py            # zenve run — main entry point
│   ├── snapshot.py         # zenve snapshot
│   ├── pipeline.py         # zenve pipeline
│   ├── status.py           # zenve status
│   ├── init.py             # zenve init — scaffold .zenve/
│   ├── doctor.py           # zenve doctor — validate repo setup
│   └── agent.py            # zenve agents … (sub-typer)
├── core/                   # Pure config/discovery helpers
│   ├── config.py           # load_project_settings() → ProjectSettings
│   ├── discovery.py        # discover_agents() → list[DiscoveredAgent]
│   ├── env.py              # load_env() → Env (reads env vars)
│   ├── pipeline.py         # next_label() pipeline transitions
│   └── console.py          # print_logo()
├── runtime/                # Local execution concerns
│   ├── executor.py         # run_agent() — claim → adapter → label transition
│   ├── parallel.py         # run_all() — asyncio gather over agents
│   └── commit.py           # git CLI wrappers (add / commit / push via subprocess)
├── integrations/           # External API clients (one subpackage per provider)
│   └── github/
│       ├── client.py       # GitHubClient — thin httpx wrapper over GitHub REST v3
│       ├── labels.py       # claim_item(), transition() — label management
│       └── snapshot.py     # build_snapshot(), write_snapshot()
├── events/
│   ├── emitter.py          # EventEmitter — writes .zenve/events.log + optional webhook
│   └── types.py            # Event type constants
└── models/
    ├── settings.py         # ProjectSettings, AgentSettings (Pydantic)
    ├── snapshot.py         # Snapshot model
    └── run_result.py       # RunResultFile, RunItem, TokenUsage, PipelineTransition
```

## Layer Rules

- **`commands/`** — thin wrappers only. Parse CLI args, call `core/` + `runtime/`, print output. No business logic.
- **`core/`** — stateless config/discovery. No I/O beyond reading `.zenve/`. No GitHub calls.
- **`runtime/`** — local execution: subprocess git, async agent runs. No GitHub REST API calls.
- **`integrations/`** — external API clients. Each provider gets its own subdirectory. No subprocess, no git.
- **`models/`** — Pydantic models only. No logic.

## `.zenve/` Folder Convention

The CLI never scaffolds `.zenve/` (except via `zenve init`). Expected layout in a user's repo:

```
.zenve/
├── settings.json           # ProjectSettings — project name, branch, pipeline, etc.
├── snapshot.json           # Written by `zenve snapshot` / `zenve run`
├── events.log              # Appended by EventEmitter on every run
└── agents/
    └── {name}/
        ├── settings.json   # AgentSettings — label, adapter, model, picks_up
        └── runs/
            └── {run_id}.json  # RunResultFile written after each run
```

## Key Models

### `ProjectSettings` (`.zenve/settings.json`)
| Field | Default | Description |
|---|---|---|
| `project` | required | Project/org slug |
| `default_branch` | `"main"` | Branch to push commits to |
| `commit_message_prefix` | `"[zenve]"` | Prefix for auto-commits |
| `run_timeout_seconds` | `600` | Global run timeout |
| `pipeline` | `{}` | Label → next-label map for pipeline transitions |

### `AgentSettings` (`.zenve/agents/{name}/settings.json`)
| Field | Default | Description |
|---|---|---|
| `name` | required | Agent slug (must match directory name) |
| `model` | `"claude-sonnet-4-6"` | LLM model |
| `adapter_type` | `"claude_code"` | Adapter (`claude_code`, `open_code`) |
| `enabled` | `true` | Skip if false |
| `github_label` | required | GitHub label this agent claims |
| `timeout_seconds` | `300` | Per-agent timeout |
| `picks_up` | `"issues"` | `issues`, `pull_requests`, `both`, `none` |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | yes | GitHub PAT with repo + issues scope |
| `ZENVE_RUN_ID` | yes | Unique ID for this run |
| `ANTHROPIC_API_KEY` | yes | Anthropic key passed to agents |
| `ZENVE_WEBHOOK_URL` | no | Optional webhook for events |
| `ZENVE_WEBHOOK_SECRET` | no | HMAC secret for webhook signature |

## `run` Command Flow

1. `load_env()` — validate required env vars
2. `load_project_settings()` — read `.zenve/settings.json`
3. `discover_agents()` — scan `.zenve/agents/*/settings.json`
4. `GitHubClient` — fetch issues, PRs, branches → `Snapshot`
5. `run_all()` — async gather over all agents via `run_agent()`
   - `filter_for_agent()` — match snapshot items by label + `picks_up`
   - `claim_item()` — assign bot login via GitHub API
   - `adapter.execute(ctx)` — run the agent subprocess
   - `transition()` — swap GitHub label per pipeline map
   - Write `RunResultFile` to `.zenve/agents/{name}/runs/{run_id}.json`
6. `commit_agents()` — `git add .zenve/agents && git commit && git push`
7. `EventEmitter.emit()` — append to `.zenve/events.log`, fire webhook

## Adding a New Integration

Create `integrations/{provider}/` with its own `__init__.py` and client module. Follow the same pattern as `integrations/github/` — a thin httpx (or similar) wrapper. Never put subprocess or git logic in `integrations/`.

## Adding a New Command

1. Create `commands/{name}.py` with a `cmd(repo_root, ...)` function
2. Register in `cli.py` with `@app.command()`
3. Keep the command thin — delegate to `core/` or `runtime/`
