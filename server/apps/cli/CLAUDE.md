# CLAUDE.md — zenve CLI

Python CLI (`typer`) that runs autonomous agents against a GitHub repo.

**Always update this file when making architectural changes** — new modules, removed layers, changed data flow, new integrations, or any structural decision that affects how the system fits together.

## Overview

Zenve turns any GitHub repository into an autonomously evolving project. Drop a `.zenve/` folder into your repo, define agents, configure a pipeline, and Zenve works through GitHub issues and PRs continuously — on a schedule, without human intervention.

The **runtime daemon** (`apps/runtime`, port 8001) is the brain: it owns workspaces, run execution, scheduling, and all `.zenve/` writes at run time. The **CLI** is a thin terminal frontend that auto-starts the daemon and delegates to it over HTTP. State lives in the repo itself; the daemon persists workspace registrations in `~/.zenve/workspaces.json`.

---

## How It Works — The Big Picture

```
Firecracker VM boots
  │
  ├── Env vars injected:
  │     ZENVE_WEBHOOK_URL (optional), ZENVE_WEBHOOK_SECRET (optional)
  │     ANTHROPIC_API_KEY
  │
  ├── git clone <repo> /workspace
  ├── cd /workspace
  └── zenve run
        │
        ├── 1. Resolve GitHub token           (gh auth token)
        ├── 2. Read .zenve/settings.json       (project config + pipeline)
        ├── 3. Discover agents                 (.zenve/agents/*)
        ├── 4. Fetch GitHub snapshot once      → .zenve/snapshot.json
        ├── 5. Reconcile stale claims          (expired TTL or orphaned zenve:claimed labels)
        ├── 6. Start all agents in parallel    (each works from same snapshot)
        ├── 7. After each agent exits:
        │       CLI posts comment to issue/PR
        │       CLI handles label transition   (pipeline in settings.json)
        ├── 8. Commit run results              back to repo
        └── 9. Emit run.completed event
```

Every agent sees the same frozen GitHub state. Whatever one agent writes to GitHub during the run is invisible to other agents until the next run. This is by design — no coordination, no locks, no race conditions.

---

## The Pipeline — Label as State Machine

Labels are the state machine. Each issue or PR carries exactly one `zenve:*` label at any time. That label determines which agent picks it up. When an agent finishes successfully, the CLI removes the current label and adds the next one — defined in the pipeline config.

**The agent never touches pipeline labels.** The CLI enforces all transitions after the agent exits.

### Example Flow

```
Issue opened with zenve:pm
        │
        ▼
  PM agent runs → writes specs
  CLI: removes zenve:pm, adds zenve:dev
        │
        ▼
  Dev agent runs → implements, opens PR
  CLI: removes zenve:dev, adds zenve:reviewer
        │
        ▼
  Reviewer agent runs → reviews, merges
  CLI: removes zenve:reviewer → end of pipeline
```

### Pipeline Config (`.zenve/settings.json`)

```json
{
  "pipeline": {
    "zenve:pm":       "zenve:dev",
    "zenve:dev":      "zenve:reviewer",
    "zenve:reviewer": null,
    "zenve:security": "zenve:reviewer",
    "zenve:docs":     null
  }
}
```

`null` = end of pipeline — label is removed, nothing picks up next.

### Rules

- **One `zenve:*` label per item at any time.** Two `zenve:*` labels = misconfiguration. CLI warns and skips the item.
- **Agent never manages pipeline labels.** Labels are exclusively managed by the CLI after agent exit.
- **Humans can intervene** by manually changing labels — add `zenve:dev` back to force rework.
- **Any topology is valid** — linear, branching, loops, skip stages.

---

## Structure

The run engine (config, discovery, events, GitHub client, git/worktree helpers, models, executor, parallel) lives in **`packages/engine`** (`zenve_engine`). The CLI is a thin presentation layer over it.

```
src/zenve_cli/
├── cli.py                  # Typer app + command registration
├── config.py               # Settings, get_settings (pydantic-settings)
├── commands/               # One file per CLI command (thin wrappers)
│   ├── run.py              # zenve run — TUI + dirty-tree checks, calls zenve_engine
│   ├── snapshot.py         # zenve snapshot — delegates to runtime POST /snapshot
│   ├── pipeline.py         # zenve pipeline
│   ├── status.py           # zenve status
│   ├── init.py             # zenve init — scaffold .zenve/
│   ├── doctor.py           # zenve doctor — validate repo setup
│   ├── agent.py            # zenve agent … (sub-typer)
│   ├── env.py              # zenve env
│   ├── skill.py            # zenve skills …
│   ├── workspace.py        # zenve workspaces … (talks to runtime daemon)
│   └── ui.py               # questionary wizard styles
├── console/                # Presentation: logo, theme, formatters, TUI
│   ├── tui.py              # ZenveTUI — Textual app, renders live agent status + tool calls
│   ├── theme.py            # color scheme constants
│   ├── logo.py             # ZENVE ASCII art, printed on every command
│   └── formatters.py       # formats tool call events for TUI display
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
    └── client.py           # httpx client to the runtime daemon: runtime_request, ensure_runtime, resolve_workspace_id, report_error
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
- **`init` is a composition** — it calls the same service methods as `zenve agent add` and `zenve skills add`, never re-implements them inline.

**Violations to flag:**
- Any business logic (loops, conditionals, data construction) inside a `commands/` file
- `from zenve_cli.utils.scaffolding import ...` inside `commands/`
- Logic duplicated across two `commands/` files — extract to a service instead
- Any import of deleted packages: `zenve_config`, `zenve_models`, `zenve_services`, `zenve_utils`

---

## `.zenve/` Folder Convention

Lives inside the user's GitHub repo. Version-controlled alongside the code.

```
.zenve/
  settings.json                      ← project config + pipeline definition
  snapshot.json                      ← written fresh each run, never committed
  events.log                         ← appended by EventEmitter on every run
  claims.json                        ← live claim tracking, not committed
  agents/
    {agent-name}/
      settings.json                  ← agent config (label, adapter, model, timeout)
      SOUL.md                        ← who this agent is (read by adapter)
      AGENTS.md                      ← what this agent does and how (read by adapter)
      HEARTBEAT.md                   ← checklist the agent follows each run (read by adapter)
      memory/                        ← persistent files the agent reads/writes (committed)
      runs/
        {run_id}.json                ← result of each run (committed)
```

`snapshot.json` and `claims.json` are **never committed** — ephemeral, regenerated each run.

The CLI never scaffolds `.zenve/` (except via `zenve init`). Any directory inside `.zenve/agents/` is treated as an agent automatically — no registration, no manifest.

### Agent Files

**SOUL.md** — who the agent is. Personality, role, values. Foundation of the system prompt.

**AGENTS.md** — what the agent does and how. Specific instructions for this agent's role.

**HEARTBEAT.md** — checklist the agent follows each run. Keeps behavior consistent.

**memory/** — persistent files committed back to the repo after each run. Each agent defines its own memory structure (e.g. `memory/scratch.md`, `memory/project_state.md`, `memory/review_patterns.md`).

---

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
| `slug` | required | Unique machine identifier, matches directory name |
| `name` | required | Human-readable display name |
| `adapter_type` | `"claude_code"` | Which adapter runs this agent (`claude_code`, `open_code`) |
| `adapter_config` | `{}` | Adapter-specific options passed through to the adapter |
| `skills` | `[]` | Skill list passed to the adapter |
| `tools` | `[]` | Explicit tool allow-list — empty = no tools, no unrestricted fallback |
| `heartbeat_interval_seconds` | `0` | If >0, adapter sends periodic heartbeat events |
| `enabled` | `true` | `false` skips the agent without removing its folder |
| `github_label` | required | GitHub label this agent claims |
| `timeout_seconds` | `300` | Per-agent execution timeout |
| `picks_up` | `"issues"` | `issues`, `pull_requests`, `both`, `none` |
| `mode` | `"no_pr"` | `"artifact_pr"`, `"code_pr"`, or `"no_pr"` — see **PR Modes** below |
| `allowed_paths` | `[]` | fnmatch glob patterns restricting which files an `artifact_pr` agent may change. Empty = no restriction. |

`picks_up` values:
- `"issues"` — only open issues
- `"pull_requests"` — only open PRs
- `"both"` — issues and PRs
- `"none"` — always-on agent, runs every cycle regardless (e.g. planner)

**Tool access:** `tools` is an explicit allow-list passed as `--allowedTools`. Non-empty = restricted to those tools. Empty `[]` = no tool access at all. No unrestricted mode exists.

If a `no_pr` agent lists write-capable tools (`Write`, `Edit`, `Bash`, `NotebookEdit`), the CLI emits `agent.misconfigured` warning before the run. Run still proceeds.

---

## Default Agent Templates

| Agent | Label | picks_up | Role |
|---|---|---|---|
| planner | zenve:planner | none | Reads repo, creates issues, tracks project state. Always runs. |
| pm | zenve:pm | issues | Refines issues, adds specs, breaks down complexity |
| dev | zenve:dev | issues | Implements issues, opens PRs |
| reviewer | zenve:reviewer | pull_requests | Reviews PRs, merges or requests changes |
| security | zenve:security | both | Security audit of issues and PRs |
| docs | zenve:docs | pull_requests | Writes/updates documentation for merged changes |

---

## GitHub Snapshot

The runtime daemon fetches GitHub state and writes it to `.zenve/snapshot.json` via `POST /api/v1/workspaces/{id}/snapshot`. Both `zenve snapshot` and `zenve run` delegate this to the daemon — neither calls `zenve_engine` directly for snapshot work.

**Agents read from snapshot. Agents write to GitHub API.**
- Reading state: always from `snapshot.json`
- Writing state: GitHub API directly (create issue, push branch, open PR, post review, merge)

---

## Agent Execution Model

```
Agent starts
  │
  ├── If no_pr + write-capable tools → emit agent.misconfigured warning
  │
  ├── Filter snapshot                 ← only items matching own label + picks_up
  ├── Pick oldest unclaimed item      ← skips items with zenve:claimed label
  │
  ├── If no matching items → exit     ← emit agent.nothing_to_do, clean exit
  │
  ├── Claim item:
  │     GitHub: add zenve:claimed label
  │     Local:  write to .zenve/claims.json
  │
  ├── If mode in ("artifact_pr", "code_pr"):
  │     git fetch origin {default_branch}
  │     git worktree add -b zenve/{slug}/{number}-{run_id_short}
  │                         ./worktrees/{slug}-{run_id_short}
  │                         origin/{default_branch}
  │     (subprocess cwd = worktree path)
  │
  ├── Build RunContext → Execute adapter
  │
  └── On adapter exit:
        If mode in ("artifact_pr", "code_pr") and exit 0:
          git add -A → collect changed files
          If artifact_pr and allowed_paths set: validate every path — else status = "failed", no PR
          git commit && git push origin {branch}
          Open PR (artifact_pr → auto-merge title; code_pr → "Closes #{n}")
          If artifact_pr: PUT /pulls/{n}/merge (squash) → reset_to_remote(default_branch)
          If push/PR/merge fails → status downgraded to "failed"
        Post comment to issue/PR
        If completed: remove zenve:claimed + current label, add next pipeline label (or nothing)
        If needs_input: remove zenve:claimed, add zenve:needs-input
        If failed: remove zenve:claimed, add zenve:failed
        Remove from .zenve/claims.json
        Write runs/{run_id}.json
        If a worktree was created → git worktree remove (always, success or failure)
```

### Agent Run Outcomes

| Status | Meaning | Label result |
|---|---|---|
| `completed` | Agent finished successfully | Pipeline transition applied |
| `needs_input` | Agent flagged a blocker for human review | `zenve:needs-input` added |
| `failed` | Adapter error or non-zero exit | `zenve:failed` added |

### Claims — Two-Phase Coordination

1. **GitHub label** — `zenve:claimed` added via GitHub API. Items with this label are skipped by `pick_unclaimed()`.
2. **Local file** — `Claim` entry written to `.zenve/claims.json` with a TTL. Enables stale-claim cleanup from crashed runs.

At startup, `reconcile_claims()` cleans both: expired TTL entries and orphaned `zenve:claimed` labels on GitHub.

Each agent processes **exactly one item per run**. Multiple waiting items → picks oldest unclaimed, rest wait for next run.

---

## PR Modes & Worktree Isolation

| `mode` | Working dir | Git ops | PR | Auto-merge |
|---|---|---|---|---|
| `no_pr` | repo root | none | no | — |
| `code_pr` | isolated worktree | fetch → commit → push | open for review | no |
| `artifact_pr` | isolated worktree | fetch → commit → push → reset to origin | open & merged in same run | squash |

Branch naming: `zenve/{agent_slug}/{issue_number}-{run_id_short}` (e.g. `zenve/dev/42-abc123`). `run_id_short` = first 6 chars of run ID.

`worktrees/` is in `.gitignore`. `artifact_pr` post-merge uses `reset --hard origin/{default_branch}` (not `git clean -fd`) to preserve in-flight run-result JSON files from parallel agents.

**Concurrency caveat:** `reset_to_remote` runs in the repo root mid-run, while parallel agents may still be executing. `no_pr` agents running in repo root will see their working tree mutate when an `artifact_pr` agent finishes. Treat `no_pr` agents as tolerant of repo-root churn, or schedule them in pipeline phases that don't overlap with `artifact_pr` runs.

---

## Commit-Back Strategy

At end of every run:

```bash
git add .zenve/agents/
git commit -m "[zenve] run_abc123 — dev: completed, reviewer: needs_input"
git push origin main
```

`snapshot.json` and `claims.json` are never committed. Code changes always go through PRs — Zenve never commits directly to main.

### Pre-run Working-Tree Check

- **Outside `.zenve/`** — must be clean. Any uncommitted change aborts the run. Protects worktree agents and the post-merge `reset --hard`.
- **Inside `.zenve/`** — uncommitted changes allowed. CLI prompts to commit them as `[zenve] update .zenve config` before fetching. Required to prevent post-merge `reset --hard` from wiping local config edits.

---

## Adapter Abstraction

All agent execution goes through `zenve_adapters` — a registry keyed by `adapter_type`.

```
zenve_adapters/
  base.py          ← BaseAdapter ABC: execute(ctx) → AdapterResult
  registry.py      ← AdapterRegistry: get(adapter_type) → BaseAdapter
  claude_code/     ← Runs `claude` CLI subprocess
  open_code/       ← Runs open-source code agent
```

Each adapter receives a `RunContext` containing: `agent_dir`, `project_dir`, slugs, `run_id`, `adapter_type`, `adapter_config`, `message` (pre-built prompt), `tools`, `env_vars`, and `on_event` callback for streaming events.

The adapter emits events as it runs (`adapter.output`, `adapter.tool_call`, `adapter.tool_result`, `adapter.usage`, `adapter.error`). These stream to the TUI and event log in real time.

Adding a new adapter: implement `BaseAdapter` and register it in `AdapterRegistry`.

---

## Event Streaming

Events are emitted throughout the run. Always written to `.zenve/events.log`. POSTed to `ZENVE_WEBHOOK_URL` if set.

### Event Types

```
run.started                CLI started — agents discovered, count reported
snapshot.fetched           Snapshot written — issues/PRs found per agent label
agent.started              Individual agent process started
agent.misconfigured        no_pr agent has write-capable tools (warning, run continues)
agent.nothing_to_do        No matching unclaimed items, clean exit
agent.claimed_issue        Agent claimed an issue
agent.claimed_pr           Agent claimed a PR
agent.completed            Agent exited successfully
agent.needs_input          Agent flagged a blocker — zenve:needs-input label added
agent.failed               Agent exited with error — zenve:failed label added
pipeline.transition        CLI removed old label, added next label
pipeline.end               CLI removed label, end of pipeline (null)
run.committing             About to commit run results to repo
run.completed              All agents done, results committed
run.failed                 Run-level failure (snapshot fetch failed, git error)

adapter.output             Raw output line from the adapter subprocess
adapter.tool_call          Adapter invoked a tool
adapter.tool_result        Tool returned a result
adapter.usage              Token/cost usage update from the adapter
adapter.error              Adapter reported an error
```

Webhook signature: `X-Zenve-Signature: sha256=<hmac-sha256 of body using ZENVE_WEBHOOK_SECRET>`

---

## Run Result File

`.zenve/agents/{name}/runs/{run_id}.json` — written after each agent run, committed to repo. Permanent audit trail, no external database needed.

```json
{
  "run_id": "run_abc123",
  "agent": "dev",
  "started_at": "2026-04-20T10:00:45Z",
  "finished_at": "2026-04-20T10:04:12Z",
  "duration_seconds": 207,
  "status": "completed",
  "exit_code": 0,
  "item": { "type": "issue", "number": 42, "title": "Add JWT authentication" },
  "pipeline_transition": { "from_label": "zenve:dev", "to_label": "zenve:reviewer" },
  "token_usage": { "input_tokens": 12400, "output_tokens": 3200, "cost_usd": 0.087 },
  "error": null
}
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Anthropic key passed to agents |
| `ZENVE_WEBHOOK_URL` | no | Where to POST events |
| `ZENVE_WEBHOOK_SECRET` | no | HMAC secret for event signing |

GitHub token: resolved automatically via `gh auth token` (requires `gh` CLI authenticated — no env var needed).
Run ID: auto-generated `uuid4().hex[:12]` — no env var needed.

---

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

---

## CLI Commands

```
zenve run                          Run all enabled agents
zenve run --agent dev              Run only a specific agent
zenve run --dry-run                Show what each agent would do, no writes

zenve init                         Scaffold .zenve/ with default agent templates interactively

zenve doctor                       Validate repo setup (token, .zenve/ structure, pipeline)
zenve status                       Show last run result per agent
zenve snapshot                     Fetch and display current GitHub snapshot (debug)
zenve pipeline                     Display and validate pipeline map from settings.json

zenve agent ls                     List all agents + enabled/disabled status
zenve agent logs <name>            Show run history for a specific agent
zenve agent enable <name>          Enable a disabled agent
zenve agent disable <name>         Disable an agent without removing it
zenve agent add                    Scaffold a new agent interactively
zenve agent update <name>          Update an existing agent's settings
```

---

## Local Development

```bash
cd my-project
gh auth login                       # authenticate once
export ANTHROPIC_API_KEY=sk-ant-...

zenve doctor                        # verify setup
zenve run --dry-run                 # see what would happen, no writes
zenve run                           # full run
```

Same CLI, same behavior as inside the VM.

---

## Adding a New Integration

Create `integrations/{provider}/` with its own `__init__.py` and client module. Follow the same pattern as `integrations/github/` — a thin httpx (or similar) wrapper. Never put subprocess or git logic in `integrations/`.

## Adding a New Command

1. Create `commands/{name}.py` with a `cmd(repo_root, ...)` function
2. Register in `cli.py` with `@app.command()`
3. Keep the command thin — delegate to `core/` or `runtime/`

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| State storage | GitHub repo (`.zenve/` folder) | No external DB. Inspectable, git-versioned, portable. |
| GitHub state | Snapshot once at CLI start | No inter-agent coordination. Deterministic. |
| Agent discovery | Directory scan of `.zenve/agents/` | Add a folder, agent is live. No registration. |
| Agent parallelism | All enabled agents start simultaneously | Each works from same snapshot. No conflicts by design. |
| Label as state machine | One `zenve:*` label per item | GitHub is the pipeline state. Human-inspectable, human-editable. |
| Label transitions | CLI-owned, defined in pipeline config | Agent never touches pipeline labels. Consistent and reliable. |
| Claims | `zenve:claimed` label + `claims.json` TTL | Two-phase: GitHub label prevents double-pick, local file enables stale-claim cleanup. |
| Run outcomes | `completed` / `needs_input` / `failed` | `needs_input` surfaces blockers without failing the run. |
| One item per agent per run | Enforced by executor | Bounded run time. Atomic failures. |
| Adapter abstraction | `zenve_adapters` registry | Swappable agent runtimes without changing the CLI. |
| GitHub token | `gh auth token` | No env var management. Uses existing `gh` CLI session. |
| Run ID | Auto-generated `uuid4().hex[:12]` | No env var needed. Unique per run. |
| Commit-back | Run results only | Code changes via PRs only. Never direct commits to main. |
| Tool access | Explicit allow-list, no fallback | `tools: []` = no tools. No `--dangerously-skip-permissions` escape hatch. |

---

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
