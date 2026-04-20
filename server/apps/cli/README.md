# zenve-cli

Autonomous agent runtime for a GitHub repo. No daemon, no server, no database — state lives in `.zenve/` inside the repo.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design.

## Install

The CLI is a uv workspace member. From `server/`:

```bash
uv sync --package zenve-cli
```

## Environment

Required:

| Var | Purpose |
|---|---|
| `GITHUB_TOKEN` | PAT with `repo` scope |
| `ZENVE_RUN_ID` | unique ID for this run |
| `ZENVE_REPO_URL` | full HTTPS clone URL |
| `ANTHROPIC_API_KEY` | for the Claude Code adapter |

Optional:

| Var | Purpose |
|---|---|
| `ZENVE_WEBHOOK_URL` | POST structured events here |
| `ZENVE_WEBHOOK_SECRET` | HMAC-SHA256 secret for `X-Zenve-Signature` |

## Commands

```
zenve start                    Run all enabled agents
zenve start --agent dev        Run only one agent
zenve start --dry-run          Show plan, no writes
zenve snapshot                 Fetch GitHub state → .zenve/snapshot.json
zenve pipeline                 Display + validate the pipeline
zenve status                   Last run per agent
zenve agent list               List agents and enabled/disabled status
zenve agent logs <name>        Run history for an agent
zenve agent enable <name>      Enable an agent
zenve agent disable <name>     Disable an agent
```

All commands accept `--repo PATH` (default `.`).

## Repo layout expected

The CLI does **not** scaffold. Author `.zenve/` by hand:

```
.zenve/
  settings.json              project config + pipeline map
  agents/
    {name}/
      settings.json          label, model, picks_up, enabled
      SOUL.md
      AGENTS.md
      HEARTBEAT.md
      memory/                persisted between runs
      runs/                  run result files (committed)
```

`.zenve/snapshot.json` is ephemeral and never committed.

## Local dev loop

```bash
cd my-project
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=sk-ant-...
export ZENVE_RUN_ID=local_$(date +%s)
export ZENVE_REPO_URL=https://github.com/owner/my-project

uv run --package zenve-cli zenve start --dry-run
uv run --package zenve-cli zenve start
```

Or via the `justfile` at `server/`:

```bash
just cli start --dry-run
```

## Execution model

1. Validate env.
2. Load `.zenve/settings.json` and scan `.zenve/agents/*` (skip `enabled: false`).
3. Fetch a fresh GitHub snapshot → `.zenve/snapshot.json`.
4. `asyncio.gather` over all enabled agents:
   - Filter snapshot by `github_label` + `picks_up`.
   - Claim the oldest unclaimed item (assign viewer + `in-progress` label).
   - Invoke the adapter (`claude_code` / `open_code`) against the agent dir.
   - Write `.zenve/agents/{name}/runs/{run_id}.json`.
   - Post-exit label transition using the pipeline map.
5. `git add .zenve/agents`; commit with `[zenve]` prefix; push.

`--dry-run` skips claim, adapter execution, label writes, and commit.

## Events

Every stage emits a structured event to `.zenve/events.log` (one JSON per line) and, if `ZENVE_WEBHOOK_URL` is set, POSTs the same JSON signed with `X-Zenve-Signature: sha256=<hmac>`.

See [ARCHITECTURE.md](./ARCHITECTURE.md#event-streaming) for the event-type list.
