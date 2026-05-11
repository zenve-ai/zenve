# CLAUDE.md — Zenve

Zenve is an autonomous agent runner. It reads a `.zenve/` config from a repo, discovers configured agents, claims open GitHub issues/PRs, runs each agent (via Claude Code, opencode, etc.), and commits/PR-submits results.

## Architecture

**The runtime daemon is the brain. The CLI and React UI are thin frontends.**

All run execution, scheduling, and workspace management live in the runtime daemon (`apps/runtime`, port 8001). The CLI is a terminal frontend that auto-starts the daemon and talks to it over HTTP. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design — Claude must respect it when making architectural changes.

## Monorepo Layout

```
server/
├── apps/
│   ├── api/        # Deployable FastAPI app (JWT + API key auth, org/agent management)
│   ├── cli/        # Typer CLI — terminal frontend, thin wrapper over engine + runtime HTTP
│   └── runtime/    # Headless daemon (port 8001) — owns workspaces, scheduling, run execution
└── packages/
    ├── engine/     # Run executor: discovers agents, calls adapters, writes .zenve/ results
    └── adapters/   # Adapter types: RunContext, RunResult, BaseAdapter, *Config

ui/                 # React SPA (future web frontend, same HTTP API as CLI)
```

**Dependency direction** (one-way, no cycles):

```
apps/cli     → zenve-engine, zenve-adapters, runtime HTTP
apps/runtime → zenve-engine
apps/api     → zenve-adapters
zenve-engine → zenve-adapters
```

Apps never import from each other. Engine never imports from CLI.

## Sub-project Docs

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — canonical system design: runtime-as-brain, CLI/UI as frontends, auto-start, run flow, scheduling ownership
- [`server/CLAUDE.md`](server/CLAUDE.md) — FastAPI monorepo: layer rules, auth model, naming rules, dev commands, violations to flag
- [`server/apps/runtime/CLAUDE.md`](server/apps/runtime/CLAUDE.md) — runtime daemon: endpoints, workspace registry, on-disk contract, roadmap
- [`server/apps/cli/CLAUDE.md`](server/apps/cli/CLAUDE.md) — CLI: commands, layer rules, `.zenve/` convention, env vars, run flow, table style
- [`server/packages/engine/CLAUDE.md`](server/packages/engine/CLAUDE.md) — engine: public API, run lifecycle, external deps, structure rules
- [`ui/CLAUDE.md`](ui/CLAUDE.md) — React SPA: stack, structure, Redux/RTK Query, routing, component rules
