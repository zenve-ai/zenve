# Zenve CLI — Architecture Spec

## Overview

Zenve is a CLI tool that turns any GitHub repository into an autonomously evolving project. Drop a `.zenve/` folder into your repo, define your agents, configure a pipeline, and Zenve will work through your GitHub issues and PRs continuously — on a schedule, without human intervention.

The CLI is the entire runtime. There is no daemon, no server, no database. State lives in the repo itself.

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

The agent never touches pipeline labels. The CLI enforces all transitions after the agent exits.

### Example Flow

```
Issue opened with zenve:pm
        │
        ▼
  PM agent runs
  → writes specs, breaks down requirements
  CLI: removes zenve:pm, adds zenve:dev
        │
        ▼
  Dev agent runs
  → implements, opens PR
  CLI: removes zenve:dev, adds zenve:reviewer
        │
        ▼
  Reviewer agent runs
  → reviews diff, merges if clean
  CLI: removes zenve:reviewer → end of pipeline
  → if changes needed: adds zenve:dev back (dev picks up next run)
```

### Pipeline Config

Defined in `.zenve/settings.json`:

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

`null` means end of pipeline — label is removed, nothing picks up next.

### Rules

- **One `zenve:*` label per item at any time.** An issue or PR with two `zenve:*` labels is a misconfiguration. The CLI warns and skips the item.
- **The agent never manages pipeline labels.** Labels are managed exclusively by the CLI after agent exit.
- **Humans can intervene** by manually changing labels — add `zenve:dev` back to force a rework, add `zenve:security` to route something through the security agent.
- **Any topology is valid** — linear pipelines, branching paths, loops, agents that skip stages. It's just a map.

---

## The `.zenve/` Folder

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
      memory/                        ← persistent files the agent reads/writes
      runs/
        {run_id}.json                ← result of each run (committed)
```

Any directory inside `.zenve/agents/` is treated as an agent. The CLI discovers them automatically — no registration, no manifest. Add a folder with a `settings.json`, the agent is live on the next run.

`snapshot.json` and `claims.json` are **never committed** — ephemeral, regenerated or updated each run.

### `.zenve/settings.json`

```json
{
  "project": "my-saas-app",
  "description": "A SaaS app for managing projects",
  "default_branch": "main",
  "commit_message_prefix": "[zenve]",
  "run_timeout_seconds": 600,
  "pipeline": {
    "zenve:pm":       "zenve:dev",
    "zenve:dev":      "zenve:reviewer",
    "zenve:reviewer": null,
    "zenve:security": "zenve:reviewer",
    "zenve:docs":     null,
    "zenve:planner":  null
  }
}
```

### `.zenve/agents/{name}/settings.json`

```json
{
  "slug": "dev",
  "name": "Developer Agent",
  "adapter_type": "claude_code",
  "adapter_config": {},
  "skills": [],
  "tools": [],
  "heartbeat_interval_seconds": 0,
  "enabled": true,
  "github_label": "zenve:dev",
  "timeout_seconds": 300,
  "picks_up": "issues"
}
```

| Field | Default | Description |
|---|---|---|
| `slug` | required | Unique machine identifier, matches directory name |
| `name` | required | Human-readable display name |
| `adapter_type` | `"claude_code"` | Which adapter runs this agent (`claude_code`, `open_code`) |
| `adapter_config` | `{}` | Adapter-specific options passed through to the adapter |
| `skills` | `[]` | Skill list passed to the adapter |
| `tools` | `[]` | Tool allow-list passed to the adapter |
| `heartbeat_interval_seconds` | `0` | If >0, adapter sends periodic heartbeat events |
| `enabled` | `true` | `false` skips the agent without removing its folder |
| `github_label` | required | GitHub label this agent claims |
| `timeout_seconds` | `300` | Per-agent execution timeout |
| `picks_up` | `"issues"` | `issues`, `pull_requests`, `both`, `none` |

`picks_up` controls what the agent looks for in the snapshot:
- `"issues"` — only open issues
- `"pull_requests"` — only open PRs
- `"both"` — issues and PRs
- `"none"` — always-on agent, runs every cycle regardless (e.g. planner)

---

## GitHub Snapshot

The CLI fetches GitHub state once at startup and writes it to `.zenve/snapshot.json`. All agents read from this file — never from the GitHub API for reading state.

```json
{
  "fetched_at": "2026-04-20T10:00:00Z",
  "run_id": "run_abc123",
  "issues": [
    {
      "number": 42,
      "title": "Add JWT authentication",
      "body": "We need JWT auth for the API...",
      "labels": ["zenve:dev"],
      "assignees": [],
      "state": "open",
      "created_at": "2026-04-19T08:00:00Z",
      "comments": [
        {
          "author": "alice",
          "body": "Should use RS256.",
          "created_at": "2026-04-19T09:00:00Z"
        }
      ]
    }
  ],
  "pull_requests": [
    {
      "number": 47,
      "title": "feat: add rate limiting",
      "body": "Closes #41",
      "labels": ["zenve:reviewer"],
      "state": "open",
      "head": "feat/rate-limiting",
      "base": "main",
      "draft": false,
      "comments": []
    }
  ],
  "branches": ["main", "feat/rate-limiting", "feat/jwt-auth"]
}
```

**Agents read from snapshot. Agents write to GitHub API.**

- Reading state: always from `snapshot.json`
- Writing state: GitHub API directly (create issue, push branch, open PR, post review, merge)

---

## Agent Execution Model

Every agent — regardless of role — follows the same lifecycle:

```
Agent starts
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
  ├── Build RunContext                ← agent dir, project dir, snapshot message, env vars
  ├── Execute adapter                 ← adapter.execute(ctx) → runs SOUL.md + AGENTS.md + HEARTBEAT.md
  │
  └── On adapter exit:
        Post comment to issue/PR     ← "Run complete / needs input / failed"
        If completed:
          Remove zenve:claimed + current label
          Add next pipeline label (or nothing if null)
        If needs_input:
          Remove zenve:claimed
          Add zenve:needs-input
        If failed:
          Remove zenve:claimed
          Add zenve:failed
        Remove from .zenve/claims.json
        Write run result → runs/{run_id}.json
```

### Agent Run Outcomes

An agent run has three possible outcomes:

| Status | What it means | Label result |
|---|---|---|
| `completed` | Agent finished successfully | Pipeline transition applied |
| `needs_input` | Agent flagged a blocker for human review | `zenve:needs-input` added |
| `failed` | Adapter error or non-zero exit | `zenve:failed` added |

The adapter signals `needs_input` via its `outcome` field. The CLI reads this and routes accordingly.

### Filtered Snapshot

Before picking an item the executor filters the snapshot:
- Match `github_label` against item labels
- Respect `picks_up`: `issues` → only issues, `pull_requests` → only PRs, `both` → either
- `picks_up: none` → skip snapshot filtering, always run

### Claims — Two-Phase Coordination

Claiming is two-phase to prevent double-pick across overlapping VM runs:

1. **GitHub label** — `zenve:claimed` is added via GitHub API. Items with this label are skipped by `pick_unclaimed()`.
2. **Local file** — A `Claim` entry is written to `.zenve/claims.json` with a TTL. This lets the CLI detect stale claims from previous crashed runs.

At startup, `reconcile_claims()` cleans up both sources:
- Expired TTL entries in `claims.json` → remove `zenve:claimed` from GitHub, remove from file
- Orphaned `zenve:claimed` labels on GitHub not in `claims.json` → same cleanup

If adding `zenve:claimed` to GitHub fails (already claimed by another run), the agent emits `agent.nothing_to_do` and exits cleanly.

### One Item Per Run

Each agent processes exactly one issue or PR per run. Bounded run time, atomic failures. If multiple items are waiting, the agent picks the oldest unclaimed one (sorted by `created_at`, then `number`). The rest wait for the next run.

---

## Adapter Abstraction

The CLI does not directly invoke Claude Code. All agent execution goes through the `zenve_adapters` package — a separate package that provides a registry of adapters keyed by `adapter_type`.

```
zenve_adapters/
  base.py          ← BaseAdapter ABC: execute(ctx) → AdapterResult
  registry.py      ← AdapterRegistry: get(adapter_type) → BaseAdapter
  claude_code/     ← Runs `claude` CLI subprocess
  open_code/       ← Runs open-source code agent
```

Each adapter receives a `RunContext` (built by the executor) containing:
- `agent_dir` — path to the agent's `.zenve/agents/{name}/` folder (where SOUL.md, AGENTS.md, HEARTBEAT.md, memory/ live)
- `project_dir` — path to the repo root
- `agent_slug`, `agent_name`, `project_slug`, `project_description`
- `run_id`, `adapter_type`, `adapter_config`
- `message` — pre-built prompt string with run metadata, issue/PR body, and comments
- `heartbeat` — whether the adapter should emit periodic heartbeat events
- `tools` — optional tool allow-list
- `env_vars` — environment variables to inject into the subprocess
- `on_event` — callback for streaming events back to the emitter

The adapter emits events as it runs (`adapter.output`, `adapter.tool_call`, `adapter.tool_result`, `adapter.usage`, `adapter.error`). These stream to the TUI and event log in real time.

Adding a new adapter: implement `BaseAdapter` and register it in `AdapterRegistry`.

---

## Agent Files

### SOUL.md

Who the agent is. Personality, role, values. Foundation of the system prompt.

```markdown
# Developer Agent

You are a senior software engineer working autonomously on a codebase.
You write clean, well-tested code. You follow existing patterns in the codebase.
You never break existing functionality. When in doubt, do less and document why.
```

### AGENTS.md

What the agent does and how. Specific instructions for this agent's role.

```markdown
# Developer Agent — Instructions

## Your Job
Pick up a GitHub issue, implement it, open a pull request.

## How To Work
1. Read the issue carefully. Understand what is being asked.
2. Explore the codebase to understand existing patterns.
3. Implement the change. Write tests if the project has them.
4. Commit with a clear message referencing the issue number.
5. Push your branch and open a PR against main.
6. PR title: match the issue title. PR body: "Closes #{issue_number}".

## Rules
- One PR per issue. Never bundle multiple issues.
- Never push directly to main.
- Never modify files outside the scope of the issue.
- If the issue is unclear, post a comment explaining what's unclear and exit.
```

### HEARTBEAT.md

The checklist the agent follows each run. Keeps behavior consistent.

```markdown
# Developer Agent — Heartbeat Checklist

- [ ] Read my assigned issue from the snapshot
- [ ] Understand what needs to be implemented
- [ ] Check if a branch already exists for this issue
- [ ] Implement following AGENTS.md instructions
- [ ] Open a PR and link it to the issue
- [ ] Update memory/scratch.md if I learned something useful
```

### memory/

Persistent files committed back to the repo after each run. Each agent defines its own memory structure. Examples:

- `memory/project_state.md` — planner's running understanding of the project
- `memory/scratch.md` — developer's notes on codebase patterns and conventions
- `memory/review_patterns.md` — reviewer's accumulated standards for this codebase

---

## Default Agent Templates

Zenve ships templates for common roles. `zenve init` scaffolds these. Users modify freely or create entirely new agent types.

| Agent | Label | picks_up | Role |
|---|---|---|---|
| planner | zenve:planner | none | Reads repo, creates issues, tracks project state. Always runs. |
| pm | zenve:pm | issues | Refines issues, adds specs, breaks down complexity |
| dev | zenve:dev | issues | Implements issues, opens PRs |
| reviewer | zenve:reviewer | pull_requests | Reviews PRs, merges or requests changes |
| security | zenve:security | both | Security audit of issues and PRs |
| docs | zenve:docs | pull_requests | Writes/updates documentation for merged changes |

The planner is the only always-on agent (`picks_up: none`). All others are label-driven. Users can define any number of additional custom agents — the CLI treats all agents identically.

---

## Console & TUI

The `console/` package provides live output during a run using [Textual](https://textual.textualize.io/).

```
console/
  tui.py          ← ZenveTUI — Textual app, renders live agent status + tool calls
  theme.py        ← color scheme constants
  logo.py         ← ZENVE ASCII art, printed on every command
  formatters.py   ← formats tool call events for TUI display
```

`ZenveTUI` subscribes to events emitted via `EventEmitter`. As adapter events arrive (`adapter.tool_call`, `adapter.output`, `adapter.usage`), the TUI renders them in real time — tool calls, output, token usage per agent.

The TUI is active during `zenve run`. Other commands (`zenve snapshot`, `zenve status`, etc.) use plain terminal output.

---

## Event Streaming

The CLI emits structured events throughout the run. Posted to webhook in real time if `ZENVE_WEBHOOK_URL` is set. Always written to `.zenve/events.log` regardless.

### Event Shape

```json
{
  "run_id": "run_abc123",
  "timestamp": "2026-04-20T10:00:42Z",
  "type": "agent.claimed_issue",
  "agent": "dev",
  "data": {
    "number": 42,
    "title": "Add JWT authentication"
  }
}
```

### Event Types

```
run.started                CLI started — agents discovered, count reported
snapshot.fetched           Snapshot written — issues/PRs found per agent label
agent.started              Individual agent process started
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

### Webhook Security

```
X-Zenve-Signature: sha256=<hmac-sha256 of body using ZENVE_WEBHOOK_SECRET>
X-Zenve-Run-Id: run_abc123
```

---

## Run Result File

Each agent writes `.zenve/agents/{name}/runs/{run_id}.json` after completing:

```json
{
  "run_id": "run_abc123",
  "agent": "dev",
  "started_at": "2026-04-20T10:00:45Z",
  "finished_at": "2026-04-20T10:04:12Z",
  "duration_seconds": 207,
  "status": "completed",
  "exit_code": 0,
  "item": {
    "type": "issue",
    "number": 42,
    "title": "Add JWT authentication"
  },
  "pipeline_transition": {
    "from_label": "zenve:dev",
    "to_label": "zenve:reviewer"
  },
  "token_usage": {
    "input_tokens": 12400,
    "output_tokens": 3200,
    "cost_usd": 0.087
  },
  "error": null
}
```

`status` is one of `completed`, `needs_input`, or `failed`.

Committed back to the repo. Permanent audit trail. No external database needed.

---

## Commit-Back Strategy

At end of every run the CLI commits to the default branch:

1. **Run result files** — `.zenve/agents/*/runs/{run_id}.json`

```bash
git add .zenve/agents/
git commit -m "[zenve] run_abc123 — dev: completed, reviewer: needs_input"
git push origin main
```

`snapshot.json` and `claims.json` are **never committed** — ephemeral, regenerated every run.

Code changes always go through PRs. Zenve never commits directly to main.

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

zenve agents list                  List all agents + enabled/disabled status
zenve agents logs <name>           Show run history for a specific agent
zenve agents enable <name>         Enable a disabled agent
zenve agents disable <name>        Disable an agent without removing it
zenve agents add                   Scaffold a new agent interactively
zenve agents update <name>         Update an existing agent's settings
```

---

## Environment Variables

```
ANTHROPIC_API_KEY         For the adapter (required)
ZENVE_WEBHOOK_URL         Where to POST events (optional)
ZENVE_WEBHOOK_SECRET      HMAC secret for event signing (optional)
```

GitHub token is resolved automatically via `gh auth token` (requires the `gh` CLI to be authenticated). No `GITHUB_TOKEN` env var needed.

Run ID is generated automatically (`uuid4().hex[:12]`) — no `ZENVE_RUN_ID` env var needed.

---

## Local Development

The CLI works locally without a VM:

```bash
cd my-project
gh auth login                       # authenticate once
export ANTHROPIC_API_KEY=sk-ant-...

zenve doctor                        # verify setup
zenve run --dry-run                 # see what would happen, no writes
zenve run                           # full run
```

Same CLI, same behavior as inside the VM. Use this to test `.zenve/` configuration before deploying.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| State storage | GitHub repo (`.zenve/` folder) | No external DB. Inspectable, git-versioned, portable. |
| GitHub state | Snapshot once at CLI start | No inter-agent coordination. Deterministic. |
| Agent discovery | Directory scan of `.zenve/agents/` | Add a folder, agent is live. No registration. |
| Number of agents | Fully open-ended, user-defined | 1 agent or 20 agents — CLI treats them all identically. |
| Agent parallelism | All enabled agents start simultaneously | Each works from same snapshot. No conflicts by design. |
| Label as state machine | One `zenve:*` label per item | GitHub is the pipeline state. Human-inspectable, human-editable. |
| Label transitions | CLI-owned, defined in pipeline config | Agent never touches pipeline labels. Consistent and reliable. |
| Claims | `zenve:claimed` label + `claims.json` TTL | Two-phase: GitHub label prevents double-pick, local file enables stale-claim cleanup. |
| Run outcomes | `completed` / `needs_input` / `failed` | `needs_input` surfaces blockers without failing the run. |
| Post-run comment | CLI posts comment to issue/PR | Run result visible on GitHub without reading log files. |
| One item per agent per run | Enforced by executor | Bounded run time. Atomic failures. |
| Adapter abstraction | `zenve_adapters` registry | Swappable agent runtimes without changing the CLI. |
| GitHub token | `gh auth token` | No env var management. Uses existing `gh` CLI session. |
| Run ID | Auto-generated `uuid4().hex[:12]` | No env var needed. Unique per run. |
| Commit-back | Run results only | Code changes via PRs only. Never direct commits to main. |
| Event streaming | Local file + optional webhook | Zero-config locally. Webhook enables live UI when needed. |
| TUI | Textual app in `console/` | Live adapter output (tool calls, token usage) without log-tailing. |
