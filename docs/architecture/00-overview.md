# Architecture — Overview

## Vision

A self-hosted FastAPI REST gateway that manages organizations of AI agents, executes them through pluggable adapters via Celery workers, and runs an internal heartbeat scheduler for autonomous agent operation. File-based agent identity meets programmatic orchestration — markdown on disk for inspectability, a database for queryability, and a task queue for concurrency.

## Design Principles

- **Files are the agent.** Agent identity, instructions, and memory live on disk as markdown. The gateway indexes them, never owns them.
- **Organization-scoped everything.** Every entity (agent, run, collaboration) belongs to an organization. One deployment serves multiple orgs with data isolation.
- **Adapter pattern for runtimes.** The gateway doesn't know how Claude Code or Codex work. Adapters do. New runtimes plug in without touching core.
- **Celery for execution.** Agent runs are async tasks. The gateway enqueues, workers execute. Natural concurrency, retries, and observability.
- **API-first.** No UI, no channels, no WebSocket — pure REST with token auth. Channels are a future layer on top.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Gateway                     │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ REST API  │  │ Auth     │  │ Heartbeat         │  │
│  │ Routes    │  │ Middleware│  │ Scheduler         │  │
│  │           │  │ (API Key)│  │ (APScheduler)     │  │
│  └─────┬────┘  └──────────┘  └────────┬──────────┘  │
│        │                               │              │
│  ┌─────▼───────────────────────────────▼──────────┐  │
│  │              Service Layer                      │  │
│  │  AgentService · RunService · OrgService         │  │
│  │  HeartbeatService · AdapterRegistry             │  │
│  └─────┬──────────────────────────────────────────┘  │
│        │                                              │
│  ┌─────▼──────────┐   ┌──────────────────────────┐  │
│  │  SQLAlchemy     │   │  Agent Filesystem        │  │
│  │  (Registry DB)  │   │  /data/orgs/{org}/       │  │
│  │                 │   │    .git/  ← org git repo │  │
│  │  - organizations│   │    agents/{name}/         │  │
│  │  - agents       │   │      SOUL.md             │  │
│  │  - runs         │   │      AGENTS.md           │  │
│  │  - api_keys     │   │      HEARTBEAT.md        │  │
│  └─────────────────┘   │      memory/             │  │
│                         │      runs/ (gitignored)  │  │
│                         └──────────────────────────┘  │
└───────────────────────────┬───────────────────────────┘
                            │ Celery task dispatch
                            ▼
┌───────────────────────────────────────────────────────┐
│                    Redis Broker                         │
└───────────────────────────┬───────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────┐
│                   Celery Workers                       │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │              Adapter Layer                      │   │
│  │                                                 │   │
│  │  BaseAdapter (ABC)                              │   │
│  │    ├── ClaudeCodeAdapter  (subprocess CLI)      │   │
│  │    ├── CodexAdapter       (subprocess CLI)      │   │
│  │    ├── AnthropicAPIAdapter (direct API)         │   │
│  │    └── ... (future adapters)                    │   │
│  └────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

## Data Model Summary

Four core database entities, plus a filesystem layer:

- **Organizations** — top-level tenant. All entities are org-scoped.
- **API Keys** — org-scoped, bcrypt-hashed, with granular scopes. Used by external callers.
- **Agents** — registered in DB with metadata (adapter type, status, heartbeat config). Identity files live on disk.
- **Runs** — execution records (queued → running → completed/failed/timeout). Transcripts stored on disk. Each run records `pre_commit_sha` and `post_commit_sha` for diffing.
- **Collaborations** — multi-agent group chat sessions with members, messages, and round-robin orchestration. Each turn creates a sub-run.

Filesystem mirrors the DB: `/data/orgs/{slug}/` holds a single git repo (`.git/`) with all agent directories under `agents/{slug}/`, a shared `project/` directory, and run transcripts are gitignored.

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | FastAPI | Async-native, auto-generated OpenAPI docs |
| ORM | SQLAlchemy (Mapped/mapped_column) | DB-agnostic — SQLite dev, Postgres prod |
| Validation | Pydantic + pydantic-settings | Shared models across routes, services, agents |
| Task queue | Celery + Redis | Async execution, retries, task revocation |
| Scheduler | APScheduler (in-process) | Heartbeat loop without external cron |
| Auth | bcrypt (API keys) + JWT (agent tokens) | Org-scoped keys for callers, short-lived tokens for agents |
| Templates | Jinja2 | Agent directory scaffolding at creation time |

## Chunks

| #  | Chunk                          | Depends On | Key Deliverables                                    | Status          | Impl. Date |
|----|--------------------------------|------------|-----------------------------------------------------|-----------------|------------|
| 01 | Organizations CRUD             | —          | ORM model, service, routes, Pydantic models         | implemented     | 2026-04-05 |
| 02 | API Key Auth                   | 01         | API key model, hashing, auth dependency, scopes, key routes | not started     | —          |
| 03 | Agent Filesystem & Templates   | 01         | zenve-scaffolding package, SOUL/AGENTS/RUN/HEARTBEAT templates, manifest.json, ScaffoldingService, PresetService, TemplateService, /api/v1/templates, /api/v1/presets | implemented     | 2026-04-10 |
| 04 | Agents CRUD                    | 01, 02, 03 | ORM model, service, routes, file read/write routes   | designed        | 2026-04-06 |
| 05 | Adapter Interface              | 04         | zenve-adapters package, BaseAdapter ABC, RunContext/RunResult, AdapterRegistry, config models | implemented     | 2026-04-10 |
| 06 | Concrete Adapters              | 05         | ClaudeCodeAdapter (`claude_code`), OpenCodeAdapter (`open_code`), shared execution pattern, event streaming | implemented     | 2026-04-10 |
| 07 | Celery Setup & Run Execution   | 05, 06     | Celery app, Redis broker, execute_agent_run task     | not started     | —          |
| 08 | Runs CRUD                      | 07         | ORM model, service, routes, transcript read          | not started     | —          |
| 09 | Agent Runtime Tokens (JWT)     | 02, 08     | Short-lived JWT generation, injection, validation    | not started     | —          |
| 10 | Heartbeat Scheduler            | 08         | APScheduler, heartbeat_tick, heartbeat routes        | not started     | —          |
| 11 | Collaborations Data Model      | 08         | ORM models, service, basic CRUD routes               | not started     | —          |
| 12 | Collaboration Execution Engine | 11, 05     | execute_group_run task, routing strategies, RESOLVE  | not started     | —          |
| 13 | Collaboration API & Messages   | 12         | Full REST API, message thread, cancel                | not started     | —          |
| 14 | Health & Observability         | 07, 10     | /health, /health/workers, status checks              | not started     | —          |
| 15 | Run Event System               | 05, 07, 08 | RunEvent model, on_event callback, event timeline API | not started     | —          |
| 16 | Org-Level Git Versioning       | 07, 08     | OrgRepo helper, commit-per-run lifecycle, rollback, diff endpoint, remote push, org git config | not started     | —          |

## Cross-Cutting Concerns

- **Auth model** — Two tiers: API keys for external callers (chunks 02, 04), short-lived JWT for agent runtimes (chunk 09). Org resolved from key, never from request body.
- **Dual identification** — All entities support UUID and slug lookup. UUID-first resolution, slug fallback.
- **Hybrid storage** — DB for queryable metadata, filesystem for agent identity and full transcripts.
- **Path safety** — All filesystem operations validate against path traversal. Agent dirs are sandboxed under org base_path.
- **Org-level git versioning** — Each org has one git repo at its filesystem root. The gateway commits once per run after the adapter returns, recording `pre_commit_sha` and `post_commit_sha` on the run record. Concurrent commits serialize via a per-org lock (chunk 16).

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transport | REST API | Simple, stateless, easy to test. WS later for streaming. |
| Agent identity | Markdown files on disk | Inspectable, git-friendly, proven pattern. |
| Agent registry | SQLAlchemy (DB-agnostic) | Queryable metadata. SQLite dev, Postgres prod. |
| Run results | Hybrid (DB + filesystem) | DB for metadata queries, filesystem for full transcripts. |
| Execution | Celery + Redis | Async, concurrent, retryable, decoupled from gateway. |
| Heartbeat | Internal APScheduler | Gateway owns the loop. No external cron. |
| Auth | API key with scopes | Simple, org-scoped, production-ready from day one. |
| Multi-tenancy | Organization-scoped | All entities belong to an org. One deployment, many teams. |
| Adapters | Pluggable ABC | Runtime-agnostic. New runtimes don't touch core. |
| Templates | Jinja2 on disk | Agent scaffolding from templates at creation time. |
| Identity bridging | slug/UUID dual lookup | Filesystem stays human-readable, API stays programmatic. |
| Agent auth at runtime | Short-lived JWT via env vars | Agents can discover peers without exposing org API keys. |
| Multi-agent collaboration | Group chat + Celery-driven round-robin | Gateway orchestrates turns, agents only see shared messages. |
| Org git versioning | One repo per org, commit per run | Single remote per org, coherent history, soft-delete audit trail. |
| Git commit concurrency | Per-org Redis lock around commit step only | Adapters run in parallel; commits serialize for ~100ms each. |
| Git remote push | `on_schedule` (5-min APScheduler) + manual | Default policy avoids noisy push-per-run; manual override via API. |

## Open Questions

1. **Session persistence across heartbeats** — Should agents resume the same session across heartbeat runs or start fresh? Session reuse saves tokens but adds complexity. *(affects chunks 06, 10)*
2. **Agent-to-agent communication** — Are there ad-hoc 1:1 communication needs outside collaborations? *(affects chunks 11-13)*
3. **HEARTBEAT_OK suppression** — If an agent finds nothing to do, should the gateway drop the response silently? *(affects chunks 08, 10)*
4. **File watching** — Should the gateway watch agent dirs for external edits or is the API the only write path? *(affects chunks 03, 04)*
5. **Run timeouts** — Default timeout for a run? Configurable per-agent? *(affects chunks 05, 07)*
6. **Adapter config secrets** — Should API keys for LLM providers live in adapter_config (encrypted), env vars, or a secrets store? *(affects chunks 05, 06)*
7. **Collaboration context management** — Should there be compaction/summarization after N messages? *(affects chunk 12)*
8. **Human-in-the-loop for collaborations** — Can a human post into an active collaboration mid-discussion? *(affects chunk 13)*
9. **Shared-state write conflicts** — If two agents in a collaboration edit `project/specs.md` in the same round, merge conflicts are possible. Current collaboration model serializes turns, so this is a future concern. *(affects chunks 12, 16)*
10. **History rewriting on hard delete** — Soft delete is the default. Hard-deleting an agent's history would require `git filter-repo` and is not exposed through the API. *(affects chunks 04, 16)*
