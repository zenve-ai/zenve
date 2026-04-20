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
  │     GITHUB_TOKEN, ZENVE_RUN_ID, ZENVE_REPO_URL
  │     ZENVE_WEBHOOK_URL (optional), ZENVE_WEBHOOK_SECRET (optional)
  │
  ├── git clone $ZENVE_REPO_URL /workspace
  ├── cd /workspace
  └── zenve start
        │
        ├── 1. Read .zenve/settings.json       (project config + pipeline)
        ├── 2. Discover agents                 (.zenve/agents/*)
        ├── 3. Fetch GitHub snapshot once      → .zenve/snapshot.json
        ├── 4. Filter snapshot per agent       (each agent sees only its label)
        ├── 5. Start all agents in parallel    (each works from same snapshot)
        ├── 6. After each agent exits:
        │       CLI handles label transition   (pipeline in settings.json)
        ├── 7. Commit memory + run results     back to repo
        └── 8. Emit run.completed event
```

Every agent sees the same frozen GitHub state. Whatever one agent writes to GitHub during the run is invisible to other agents until the next run. This is by design — no coordination, no locks, no race conditions.

---

## The Pipeline — Label as State Machine

Labels are the state machine. Each issue or PR carries exactly one `zenve:*` label at any time. That label determines which agent picks it up. When an agent finishes, the CLI removes the current label and adds the next one — defined in the pipeline config.

The agent never touches labels. The CLI enforces all transitions after the agent exits.

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
- **The agent never manages labels.** Labels are managed exclusively by the CLI after agent exit.
- **Humans can intervene** by manually changing labels — add `zenve:dev` back to force a rework, add `zenve:security` to route something through the security agent.
- **Any topology is valid** — linear pipelines, branching paths, loops, agents that skip stages. It's just a map.

---

## The `.zenve/` Folder

Lives inside the user's GitHub repo. Version-controlled alongside the code.

```
.zenve/
  settings.json                      ← project config + pipeline definition
  snapshot.json                      ← written fresh each run, never committed
  agents/
    {agent-name}/
      settings.json                  ← agent config (label, model, timeout)
      SOUL.md                        ← who this agent is
      AGENTS.md                      ← what this agent does and how
      HEARTBEAT.md                   ← checklist the agent follows each run
      memory/                        ← persistent files the agent reads/writes
      runs/
        {run_id}.json                ← result of each run (committed)
```

Any directory inside `.zenve/agents/` is treated as an agent. The CLI discovers them automatically — no registration, no manifest. Add a folder with a `settings.json`, the agent is live on the next run.

### `.zenve/settings.json`

```json
{
  "project": "my-saas-app",
  "repo": "owner/repo",
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
  "name": "dev",
  "display_name": "Developer Agent",
  "model": "claude-sonnet-4-5",
  "enabled": true,
  "github_label": "zenve:dev",
  "timeout_seconds": 300,
  "picks_up": "issues"
}
```

`picks_up` controls what the agent looks for in the snapshot:
- `"issues"` — only open issues
- `"pull_requests"` — only open PRs
- `"both"` — issues and PRs
- `"none"` — always-on agent, runs every cycle regardless (e.g. planner)

`enabled: false` disables the agent without removing its folder.

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
      "created_at": "2026-04-19T08:00:00Z"
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
      "draft": false
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
  ├── Read filtered snapshot            ← only items matching own label
  ├── Read own SOUL.md, AGENTS.md       ← identity and instructions
  ├── Read own HEARTBEAT.md             ← checklist for this run
  ├── Read own memory/                  ← persistent context
  │
  ├── If no matching items → exit 0     ← nothing to do, clean exit
  │
  ├── Claim one item via GitHub API     ← assign to bot + add in-progress label
  │
  ├── Run Claude Code CLI               ← do the actual work
  │
  ├── Write outputs to GitHub API       ← whatever this agent produces
  ├── Update own memory/ if needed      ← persist what was learned
  └── Write run result → runs/{run_id}.json
        │
        └── CLI takes over:
              removes current zenve:* label
              removes in-progress label
              adds next label from pipeline (or nothing if null)
```

### Filtered Snapshot

Before starting each agent the CLI writes a pre-filtered view of the snapshot scoped to that agent's label. The dev agent only sees issues labeled `zenve:dev`. The reviewer only sees PRs labeled `zenve:reviewer`. Agents never need to filter themselves.

### Work Claiming

Before starting work the agent claims the item via GitHub API:
- Assign item to a designated bot user (`zenve-bot`)
- Add `in-progress` label alongside the existing `zenve:*` label

This prevents re-picking across overlapping VM runs (edge case: long-running VM, cron fires again). If the claim fails (item already assigned), the agent skips it and picks the next unclaimed item.

After agent exits, the CLI removes `in-progress` and the current `zenve:*` label, then adds the next pipeline label.

### One Item Per Run

Each agent processes exactly one issue or PR per run. Bounded run time, atomic failures. If multiple items are waiting, the agent picks the oldest unclaimed one. The rest wait for the next run.

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

## Event Streaming

The CLI emits structured events throughout the run. Posted to webhook in real time if `ZENVE_WEBHOOK_URL` is set. Always written to local log file regardless.

### Event Shape

```json
{
  "run_id": "run_abc123",
  "timestamp": "2026-04-20T10:00:42Z",
  "type": "agent.claimed_issue",
  "agent": "dev",
  "data": {
    "issue_number": 42,
    "issue_title": "Add JWT authentication"
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
agent.failed               Agent exited with non-zero exit code
pipeline.transition        CLI removed old label, added next label
pipeline.end               CLI removed label, end of pipeline (null)
run.committing             About to commit memory + run results to repo
run.completed              All agents done, results committed
run.failed                 Run-level failure (snapshot fetch failed, git error)
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
  "output": {
    "branch_created": "feat/jwt-auth",
    "pr_opened": 51
  },
  "pipeline_transition": {
    "from": "zenve:dev",
    "to": "zenve:reviewer"
  },
  "token_usage": {
    "input_tokens": 12400,
    "output_tokens": 3200,
    "cost_usd": 0.087
  },
  "error": null
}
```

Committed back to the repo. Permanent audit trail. No external database needed.

---

## Commit-Back Strategy

At end of every run the CLI commits to the default branch:

1. **Agent memory files** — `.zenve/agents/*/memory/`
2. **Run result files** — `.zenve/agents/*/runs/{run_id}.json`

```bash
git add .zenve/agents/*/memory/
git add .zenve/agents/*/runs/
git commit -m "[zenve] run_abc123 — dev: PR #51 opened, reviewer: PR #47 merged, planner: 3 issues created"
git push origin main
```

`snapshot.json` is **never committed** — ephemeral, regenerated every run.

Code changes always go through PRs. Zenve never commits directly to main.

---

## CLI Commands

```
zenve start                        Run all enabled agents
zenve start --agent dev            Run only a specific agent
zenve start --dry-run              Show what each agent would do, no writes

zenve init                         Scaffold .zenve/ with default agent templates
zenve init --agents pm,dev,reviewer  Scaffold specific agents only

zenve status                       Show last run result per agent
zenve snapshot                     Fetch and display current GitHub snapshot (debug)
zenve pipeline                     Display pipeline map from settings.json

zenve agent list                   List all agents + enabled/disabled status
zenve agent logs <name>            Show run history for a specific agent
zenve agent enable <name>          Enable a disabled agent
zenve agent disable <name>         Disable an agent without removing it
```

---

## Environment Variables

```
GITHUB_TOKEN              GitHub PAT or App token (required)
ZENVE_RUN_ID              Unique ID for this run (required)
ZENVE_REPO_URL            Full HTTPS clone URL (required)
ANTHROPIC_API_KEY         For Claude Code CLI (required)
ZENVE_WEBHOOK_URL         Where to POST events (optional)
ZENVE_WEBHOOK_SECRET      HMAC secret for event signing (optional)
```

---

## Local Development

The CLI works locally without a VM:

```bash
cd my-project
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=sk-ant-...
export ZENVE_RUN_ID=local_$(date +%s)
export ZENVE_REPO_URL=https://github.com/owner/my-project

zenve start --dry-run    # see what would happen, no writes
zenve start              # full run
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
| Label transitions | CLI-owned, defined in pipeline config | Agent never touches labels. Consistent and reliable. |
| Work claiming | Assign to bot + `in-progress` label | Prevents double-pick. GitHub API as the lock. |
| One item per agent per run | Enforced by agent instructions | Bounded run time. Atomic failures. |
| Commit-back | Memory + run results only | Code changes via PRs only. Never direct commits to main. |
| Event streaming | Local file + optional webhook | Zero-config locally. Webhook enables live UI when needed. |

---

## What Gets Built First

In order:

1. **`zenve init`** — scaffold `.zenve/` with configurable agent selection
2. **`zenve snapshot`** — fetch GitHub state, write `snapshot.json`, standalone testable
3. **`zenve pipeline`** — validate and display pipeline from `settings.json`
4. **`zenve start --dry-run`** — discover agents, show filtered snapshot per agent, no writes
5. **`zenve start`** — full run: snapshot → parallel agents → label transitions → commit back
6. **Event emission** — `emit()` throughout, local file first, webhook second
7. **Default agent templates** — SOUL.md, AGENTS.md, HEARTBEAT.md for all six default agents
