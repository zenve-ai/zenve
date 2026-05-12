# zenve-cli

Autonomous agent runtime for a GitHub repo. No daemon, no server, no database — state lives in `.zenve/` inside the repo.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design.

## Install

```bash
uv tool install zenve-cli      # recommended
pipx install zenve-cli         # alternative
```

Upgrade:

```bash
uv tool upgrade zenve-cli
```

### From source (for development)

The CLI is a uv workspace member. From `server/`:

```bash
uv sync --package zenve-cli
```

## Environment

Required:

| Var | Purpose |
|---|---|
| `ZENVE_GH_TOKEN` | GitHub PAT with `repo` + `issues` scope (falls back to `gh auth token`) |

Per-agent (optional):

| Var | Purpose |
|---|---|
| `ZENVE_GH_{SLUG}` | Agent-specific GitHub token (e.g. `ZENVE_GH_CODE_REVIEW` for slug `code-review`) |

Optional:

| Var | Purpose |
|---|---|
| `ZENVE_WEBHOOK_URL` | POST structured events here |
| `ZENVE_WEBHOOK_SECRET` | HMAC-SHA256 secret for `X-Zenve-Signature` |

> **Note:** Run ID is generated automatically. No `ANTHROPIC_API_KEY` needed at the CLI level — agent adapters pick up their own credentials.

## Commands

```
zenve run                      Run all enabled agents
zenve run --agent dev          Run only one agent
zenve run --dry-run            Show plan, no writes
zenve snapshot                 Fetch GitHub state → .zenve/snapshot.json
zenve pipeline                 Display + validate the pipeline
zenve status                   Last run per agent
zenve init                     Scaffold .zenve/ interactively
zenve doctor                   Check repo setup
zenve agent ls                 List agents and enabled/disabled status
zenve agent logs <name>        Run history for an agent
zenve agent enable <name>      Enable an agent
zenve agent disable <name>     Disable an agent
zenve skills list              List available skills
```

All commands accept `--repo PATH` (default `.`).

## Repo layout expected

The CLI does **not** scaffold `.zenve/` by hand — use `zenve init` instead. Expected layout:

```
.zenve/
  settings.json              project config + pipeline map
  agents/
    {name}/
      settings.json          label, adapter, model, picks_up, mode
      runs/                  run result files (committed)
```

`.zenve/snapshot.json` is ephemeral and never committed.

## Local dev loop

```bash
cd my-project
export ZENVE_GH_TOKEN=ghp_...   # or: gh auth login

uv run --package zenve-cli zenve doctor
uv run --package zenve-cli zenve run --dry-run
uv run --package zenve-cli zenve run
```

Or via the `justfile` at `server/`:

```bash
just cli run --dry-run
```

## Execution model

1. Resolve GitHub token (`ZENVE_GH_TOKEN` or `gh auth token`).
2. Load `.zenve/settings.json` and scan `.zenve/agents/*` (skip `enabled: false`).
3. Fetch a fresh GitHub snapshot → `.zenve/snapshot.json`.
4. `asyncio.gather` over all enabled agents:
   - Filter snapshot by `github_label` + `picks_up`.
   - Claim the oldest unclaimed item (`zenve:claimed` label via GitHub API).
   - If `mode` is `artifact_pr` or `code_pr`: create a git worktree on a new branch.
   - Invoke the adapter (`claude_code` / `open_code`) against the agent dir.
   - On success: commit + push changes, open a PR (and auto-merge if `artifact_pr`).
   - Post-exit label transition using the pipeline map.
   - Write `.zenve/agents/{name}/runs/{run_id}.json`.
5. `git add .zenve/agents`; commit with `[zenve]` prefix; push.

`--dry-run` skips claim, adapter execution, label writes, and commit.

## Events

Every stage emits a structured event to `.zenve/events.log` (one JSON per line) and, if `ZENVE_WEBHOOK_URL` is set, POSTs the same JSON signed with `X-Zenve-Signature: sha256=<hmac>`.

See [ARCHITECTURE.md](./ARCHITECTURE.md#event-streaming) for the event-type list.

## Release workflow

When tagging a new release:

```bash
# Generate/update CHANGELOG.md
git-cliff --output CHANGELOG.md

# Commit the changelog
git add CHANGELOG.md
git commit -m "chore: update changelog for v1.0.0"

# Tag and push
git tag v1.0.0
git push && git push --tags
```

To preview only the next release (unreleased commits):

```bash
git-cliff --unreleased
```

To create a GitHub release with the changelog body:

```bash
git-cliff --unreleased --strip header | gh release create v1.0.0 --notes-file -
```
