# CLAUDE.md — zenve CLI

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full architecture spec and design rationale.

## Keeping ARCHITECTURE.md Up to Date

**Always update `ARCHITECTURE.md` when making architectural changes** — new modules, removed layers, changed data flow, new integrations, or any structural decision that affects how the system fits together. The file is the authoritative design record; if the code diverges from it, future readers (and Claude) will be misled.

Python CLI (`typer`) that runs autonomous agents against a GitHub repo.

## Structure

The run engine (config, discovery, events, GitHub client, git/worktree helpers, models, executor, parallel) lives in **`packages/engine`** (`zenve_engine`). The CLI is a thin presentation layer over it.

```
src/zenve_cli/
├── cli.py                  # Typer app + command registration
├── config.py               # Settings, get_settings (pydantic-settings)
├── commands/               # One file per CLI command (thin wrappers)
│   ├── run.py              # zenve run — TUI + dirty-tree checks, calls zenve_engine
│   ├── snapshot.py         # zenve snapshot — calls zenve_engine.snapshot()
│   ├── pipeline.py         # zenve pipeline
│   ├── status.py           # zenve status
│   ├── init.py             # zenve init — scaffold .zenve/
│   ├── doctor.py           # zenve doctor — validate repo setup
│   ├── agent.py            # zenve agents … (sub-typer)
│   ├── env.py              # zenve env
│   ├── skill.py            # zenve skills …
│   ├── workspace.py        # zenve workspaces … (talks to runtime daemon)
│   └── ui.py               # questionary wizard styles
├── console/                # Presentation: logo, theme, formatters, TUI
├── models/
│   ├── errors.py           # ZenveError + domain exceptions
│   ├── agent.py            # AgentCreate (used by build_agent_files)
│   └── github_template.py  # GitHubTemplateSummary, SkillSummary
├── services/
│   ├── template.py         # GitHubTemplateService
│   ├── scaffolding.py      # ScaffoldingService
│   ├── agent_lock.py       # AgentLockService
│   └── agent.py            # build_agent_files helper
├── utils/
│   └── scaffolding.py      # slugify, default_files, build_settings_json
└── runtime/
    └── client.py           # httpx client to the runtime daemon (NOT the engine)
```

Engine modules previously here have moved to `zenve_engine`:

| Was | Now |
|---|---|
| `zenve_cli.constants` | `zenve_engine.constants` |
| `zenve_cli.core.config` | `zenve_engine.config` |
| `zenve_cli.core.discovery` | `zenve_engine.discovery` |
| `zenve_cli.core.pipeline` | `zenve_engine.pipeline` |
| `zenve_cli.core.claims` | `zenve_engine.claims` |
| `zenve_cli.core.env` | `zenve_engine.env` |
| `zenve_cli.events.*` | `zenve_engine.events.*` |
| `zenve_cli.integrations.github.*` | `zenve_engine.github.*` |
| `zenve_cli.models.*` | `zenve_engine.models.*` |
| `zenve_cli.runtime.commit` | `zenve_engine.git.commit` |
| `zenve_cli.runtime.worktree` | `zenve_engine.git.worktree` |
| `zenve_cli.runtime.executor` | `zenve_engine.exec.executor` |
| `zenve_cli.runtime.parallel` | `zenve_engine.exec.parallel` |

## Layer Rules

- **`commands/`** — thin wrappers only. Parse CLI args, call `zenve_engine`, render output. No business logic.
- **`console/`** — pure presentation: logo, TUI, formatters, theme.
- **`runtime/client.py`** — talks to the runtime daemon over HTTP.
- **No engine logic in CLI.** Anything that reads `.zenve/`, calls GitHub, runs git, or executes adapters belongs in `zenve_engine`.

## Commands Are Like API Routes (IMPORTANT)

`commands/` is the CLI equivalent of `apps/api/routes/` in the FastAPI app. The same rules apply:

- **Thin wrappers only** — parse args, call services, print output. No business logic.
- **Only call `zenve_cli.services`** — never implement logic that belongs in a service.
- **No helper functions with logic** — if it's not pure UI (prompts, formatting), it belongs in a service or `zenve_cli.utils`.
- **Never import from `zenve_cli.utils.scaffolding` directly** — that is a service concern.
- **`init` is a composition** — it calls the same service methods as `zenve agents add` and `zenve skills add`, never re-implements them inline.

**Violations to flag:**
- Any business logic (loops, conditionals, data construction) inside a `commands/` file
- `from zenve_cli.utils.scaffolding import ...` inside `commands/`
- Logic duplicated across two `commands/` files — extract to a service instead
- Any import of deleted packages: `zenve_config`, `zenve_models`, `zenve_services`, `zenve_utils`

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

## Table Style

All commands that display lists of items must use the same Rich table style:

```python
from rich import box
from rich.table import Table

table = Table(
    box=box.ROUNDED,
    border_style="dim",
    header_style="bold cyan",
    show_lines=False,
    pad_edge=True,
)
table.add_column("COLUMN", style="cyan", no_wrap=True)
table.add_column("OTHER COLUMN", style="dim")

console.print()
console.print(table)
console.print()
```

- Column headers in ALL CAPS
- First/ID column: `style="cyan"`, `no_wrap=True`
- Timestamp columns: `style="dim"`
- Status values: use `Text("● done", style="green")` / `Text("✗ failed", style="red")`
- List commands are named `ls`, not `list`
