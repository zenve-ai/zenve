# CLAUDE.md — zenve CLI

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full architecture spec and design rationale.

## Keeping ARCHITECTURE.md Up to Date

**Always update `ARCHITECTURE.md` when making architectural changes** — new modules, removed layers, changed data flow, new integrations, or any structural decision that affects how the system fits together. The file is the authoritative design record; if the code diverges from it, future readers (and Claude) will be misled.

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
│   ├── commit.py           # git CLI wrappers (add / commit / push via subprocess)
│   └── worktree.py         # git worktree helpers (create / remove / commit-and-push)
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

## Commands Are Like API Routes (IMPORTANT)

`commands/` is the CLI equivalent of `apps/api/routes/` in the FastAPI app. The same rules apply:

- **Thin wrappers only** — parse args, call services, print output. No business logic.
- **Only call `zenve_services`** — never implement logic that belongs in a service.
- **No helper functions with logic** — if it's not pure UI (prompts, formatting), it belongs in a service or `zenve_utils`.
- **Never import from `zenve_utils.scaffolding` directly** — that is a service concern.
- **`init` is a composition** — it calls the same service methods as `zenve agents add` and `zenve skills add`, never re-implements them inline.

**Violations to flag:**
- Any business logic (loops, conditionals, data construction) inside a `commands/` file
- `from zenve_utils.scaffolding import ...` inside `commands/`
- Logic duplicated across two `commands/` files — extract to a service instead

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
| `slug` | required | Agent slug (must match directory name) |
| `name` | required | Human-readable display name |
| `adapter_type` | `"claude_code"` | Adapter (`claude_code`, `open_code`) |
| `enabled` | `true` | Skip if false |
| `github_label` | required | GitHub label this agent claims |
| `timeout_seconds` | `300` | Per-agent timeout |
| `picks_up` | `"issues"` | `issues`, `pull_requests`, `both`, `none` |
| `tools` | `[]` | Explicit tool allow-list — empty means no tools, no unrestricted fallback |
| `mode` | `"no_pr"` | `"artifact_pr"` — worktree + PR + auto-merge (squash); `"code_pr"` — worktree + PR left open for review; `"no_pr"` — runs from repo root, no worktree, no PR |
| `allowed_paths` | `[]` | Glob patterns (fnmatch) restricting which files an `artifact_pr` agent may change. Empty = no restriction. Files outside cause the run to fail before the PR is opened. |

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
   - Emit `agent.misconfigured` if `no_pr` agent has write-capable tools
   - `claim_item()` — add `zenve:claimed` label via GitHub API
   - If `mode in ("artifact_pr", "code_pr")`: `create_worktree()` on a new branch `zenve/{slug}/{number}-{run_id_short}`
   - `adapter.execute(ctx)` — run the agent subprocess (cwd = worktree for PR modes, repo root for `no_pr`)
   - If `mode in ("artifact_pr", "code_pr")` and exit 0: `stage_changes()` → optional `paths_within()` validation (artifact_pr only) → `commit_and_push()` → `gh.create_pr()`
   - If `mode == "artifact_pr"`: `gh.merge_pr()` (squash) → `reset_to_remote()` to fast-forward local main
   - `transition()` — swap GitHub label per pipeline map (only on success; for `artifact_pr`, only after merge succeeds)
   - Write `RunResultFile` to `.zenve/agents/{name}/runs/{run_id}.json`
   - If a worktree was created: `remove_worktree()` (always, success or failure)
6. `commit_agents()` — `git add .zenve/agents && git commit && git push`
7. `EventEmitter.emit()` — append to `.zenve/events.log`, fire webhook

## Adding a New Integration

Create `integrations/{provider}/` with its own `__init__.py` and client module. Follow the same pattern as `integrations/github/` — a thin httpx (or similar) wrapper. Never put subprocess or git logic in `integrations/`.

## Adding a New Command

1. Create `commands/{name}.py` with a `cmd(repo_root, ...)` function
2. Register in `cli.py` with `@app.command()`
3. Keep the command thin — delegate to `core/` or `runtime/`
