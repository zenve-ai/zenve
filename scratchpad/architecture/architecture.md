# Agent Gateway — Architecture Design Document

## 1. Vision

A self-hosted FastAPI REST gateway that manages organizations of AI agents, executes them through pluggable adapters via Celery workers, and runs an internal heartbeat scheduler for autonomous agent operation. File-based agent identity (inspired by OpenClaw) meets programmatic orchestration (inspired by Paperclip).

---

## 2. Design Principles

- **Files are the agent.** Agent identity, instructions, and memory live on disk as markdown. The gateway indexes them, never owns them.
- **Organization-scoped everything.** Every entity (agent, run, project) belongs to an organization. One gateway deployment serves multiple orgs with data isolation.
- **Adapter pattern for runtimes.** The gateway doesn't know how Claude Code or Codex work. Adapters do. New runtimes plug in without touching core.
- **Celery for execution.** Agent runs are async tasks. The gateway enqueues, workers execute. Natural concurrency, retries, and observability.
- **API-first.** No UI, no channels, no WebSocket — pure REST with token auth. Channels (Telegram, Slack) are a future layer on top.

---

## 3. High-Level Architecture

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
│  │                 │   │    agents/{name}/         │  │
│  │  - organizations│   │      SOUL.md             │  │
│  │  - agents       │   │      AGENTS.md           │  │
│  │  - runs         │   │      HEARTBEAT.md        │  │
│  │  - api_keys     │   │      memory/             │  │
│  └─────────────────┘   │      runs/ (transcripts) │  │
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

---

## 4. Data Model

### 4.1 Database (SQLAlchemy — registry + operational state)

```
organizations
  id              UUID PK
  name            VARCHAR UNIQUE
  slug            VARCHAR UNIQUE
  base_path       VARCHAR          -- e.g. /data/orgs/acme
  created_at      TIMESTAMP
  updated_at      TIMESTAMP

api_keys
  id              UUID PK
  org_id          UUID FK → organizations
  key_hash        VARCHAR          -- bcrypt hash of the API key
  name            VARCHAR          -- human label ("CI key", "dev key")
  scopes          JSONB            -- ["agents:read", "agents:write", "runs:*"]
  is_active       BOOLEAN
  created_at      TIMESTAMP
  expires_at      TIMESTAMP NULL

agents
  id              UUID PK
  org_id          UUID FK → organizations
  name            VARCHAR          -- unique within org
  slug            VARCHAR          -- unique within org
  dir_path        VARCHAR          -- absolute path to agent dir on disk
  adapter_type    VARCHAR          -- "claude_code", "codex", "anthropic_api"
  adapter_config  JSONB            -- adapter-specific settings (model, flags)
  skills          JSONB            -- ["code_review", "testing", "deployment"]
  status          ENUM             -- active, paused, error, archived
  heartbeat_interval_seconds  INT  -- 0 = disabled
  last_heartbeat_at  TIMESTAMP NULL
  created_at      TIMESTAMP
  updated_at      TIMESTAMP

runs
  id              UUID PK
  org_id          UUID FK → organizations
  agent_id        UUID FK → agents
  trigger         ENUM             -- heartbeat, manual, webhook, collaboration
  status          ENUM             -- queued, running, completed, failed, timeout
  adapter_type    VARCHAR
  started_at      TIMESTAMP NULL
  finished_at     TIMESTAMP NULL
  exit_code       INT NULL
  error_summary   TEXT NULL
  token_usage     JSONB NULL       -- {input_tokens, output_tokens, cache_read, cost_usd}
  transcript_path VARCHAR NULL     -- path to full transcript on disk
  celery_task_id  VARCHAR NULL     -- for task tracking/revocation
  collaboration_id UUID FK NULL   -- set for collaboration sub-runs
  created_at      TIMESTAMP
```

### 4.2 Filesystem (agent identity + transcripts)

```
/data/orgs/{org_slug}/
  agents/
    {agent_slug}/
      gateway.json         -- gateway-managed identity + config (see below)
      SOUL.md              -- personality, identity, role
      AGENTS.md            -- instructions, capabilities, constraints
      HEARTBEAT.md         -- autonomous checklist (what to check each wake)
      TOOLS.md             -- available tools/MCP servers (optional)
      memory/
        long_term.md       -- persistent knowledge
        scratch.md         -- working memory (agent can write to this)
      runs/
        2026-04-04T12-30-00_abc123.md   -- full transcript
        2026-04-04T13-00-00_def456.md
```

#### gateway.json (gateway-managed identity file)

Written by the gateway at scaffold time, updated when config changes via API.
Agents and adapters read this to know who they are without calling the API.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "dev-agent",
  "org_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "org_slug": "acme",
  "adapter_type": "claude_code",
  "skills": ["code_review", "testing", "deployment"],
  "status": "active",
  "gateway_url": "https://gateway.example.com/api/v1",
  "created_at": "2026-04-04T12:00:00Z"
}
```

**Design rules for gateway.json:**
- The gateway is the owner. It writes this file at creation and updates it on `PATCH /agents/{id}`.
- No credentials are stored here. Auth tokens are ephemeral and injected at runtime via env vars (see Section 9).
- Agents can read it to know their own identity, org, and available skills.
- The `id` + `slug` pairing is the bridge between the filesystem world and the API world.
- API endpoints accept both UUID and slug for agent identification (resolved UUID-first, then slug).

### 4.3 Agent Templates

When `POST /agents` creates a new agent, the gateway scaffolds from a template:

```
/data/templates/
  default/
    SOUL.md.j2
    AGENTS.md.j2
    HEARTBEAT.md.j2
    TOOLS.md.j2
```

Templates are Jinja2 with variables like `{{ agent_name }}`, `{{ org_name }}`, `{{ role }}`.

---

## 5. REST API Design

All routes prefixed with `/api/v1`. All require `Authorization: Bearer <api_key>`. Org is resolved from the API key.

### 5.1 Organizations

```
POST   /orgs                          Create org (returns first API key)
GET    /orgs                          List orgs (superadmin)
GET    /orgs/{org_id}                 Get org details
PATCH  /orgs/{org_id}                 Update org
```

### 5.2 Agents

```
POST   /agents                        Create agent (scaffolds dir from template)
  Body: { name, adapter_type, adapter_config, heartbeat_interval_seconds, template?, role? }

GET    /agents                         List agents (filtered by org from API key)
  Query: ?status=active&adapter_type=claude_code

GET    /agents/{agent_id}              Get agent details + last run summary
PATCH  /agents/{agent_id}              Update agent config/status
DELETE /agents/{agent_id}              Archive agent (soft delete, keeps files)

GET    /agents/{agent_id}/files        List files in agent dir
GET    /agents/{agent_id}/files/{path} Read a specific file (SOUL.md, etc.)
PUT    /agents/{agent_id}/files/{path} Write/update a specific file
```

### 5.3 Runs

```
POST   /runs                           Trigger a manual run
  Body: { agent_id, message?, params? }

GET    /runs                           List runs
  Query: ?agent_id=...&status=...&trigger=heartbeat&limit=50

GET    /runs/{run_id}                  Get run details
GET    /runs/{run_id}/transcript       Get full transcript from disk
DELETE /runs/{run_id}/cancel           Cancel a running task (revoke Celery task)
```

### 5.4 Heartbeats

```
GET    /heartbeats                     List heartbeat schedule for all agents
POST   /heartbeats/{agent_id}/trigger  Force an immediate heartbeat for an agent
PATCH  /heartbeats/{agent_id}          Update heartbeat interval
  Body: { interval_seconds }
```

### 5.5 Health

```
GET    /health                         Gateway health (DB, Redis, scheduler status)
GET    /health/workers                 Celery worker status
```

---

## 6. Adapter Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RunContext:
    agent_dir: str              # absolute path to agent dir
    agent_id: str               # UUID from DB
    agent_slug: str             # human-readable slug
    agent_name: str
    org_id: str
    org_slug: str
    run_id: str
    message: str | None         # user message for manual runs
    heartbeat: bool             # True if triggered by heartbeat
    adapter_config: dict        # adapter-specific config from DB
    gateway_url: str            # injected as env var for agent discovery
    agent_token: str            # short-lived JWT, injected as env var
    env_vars: dict              # extra env vars to pass

@dataclass
class RunResult:
    exit_code: int
    stdout: str                 # full output / transcript
    stderr: str
    token_usage: dict | None    # {input_tokens, output_tokens, cost_usd}
    duration_seconds: float
    error: str | None

class BaseAdapter(ABC):

    @abstractmethod
    async def execute(self, ctx: RunContext) -> RunResult:
        """Execute the agent. Called inside a Celery worker."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the runtime is available (e.g., CLI installed)."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Adapter identifier (e.g. 'claude_code')."""
        ...
```

### Example: Claude Code Adapter (sketch)

```python
class ClaudeCodeAdapter(BaseAdapter):

    def name(self) -> str:
        return "claude_code"

    async def execute(self, ctx: RunContext) -> RunResult:
        # 1. Build prompt from agent files
        soul = read_file(ctx.agent_dir / "SOUL.md")
        agents_md = read_file(ctx.agent_dir / "AGENTS.md")

        if ctx.heartbeat:
            heartbeat_md = read_file(ctx.agent_dir / "HEARTBEAT.md")
            message = f"Heartbeat check. Review your checklist:\n{heartbeat_md}"
        else:
            message = ctx.message

        # 2. Spawn claude CLI in non-interactive mode
        proc = await asyncio.create_subprocess_exec(
            "claude", "--query", message,
            "--system-prompt", soul,
            "--cwd", ctx.agent_dir,
            env={**os.environ, **ctx.env_vars},
            stdout=PIPE, stderr=PIPE
        )
        stdout, stderr = await proc.communicate()

        # 3. Parse output for token usage
        usage = parse_usage(stderr)

        return RunResult(
            exit_code=proc.returncode,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            token_usage=usage,
            duration_seconds=...,
            error=stderr.decode() if proc.returncode != 0 else None,
        )
```

---

## 7. Heartbeat Scheduler

Uses APScheduler running inside the FastAPI process:

```python
async def heartbeat_tick():
    """Runs every 30 seconds. Checks which agents are due."""
    now = utcnow()
    agents = await agent_service.get_agents_due_for_heartbeat(now)

    for agent in agents:
        # Skip if agent already has a running task
        if await run_service.has_active_run(agent.id):
            continue

        # Enqueue Celery task
        run = await run_service.create_run(
            agent_id=agent.id,
            trigger="heartbeat",
            status="queued",
        )
        execute_agent_run.delay(run_id=str(run.id))

        # Update last heartbeat timestamp
        await agent_service.update_last_heartbeat(agent.id, now)
```

The scheduler tick (e.g. 30s) is independent of each agent's `heartbeat_interval_seconds`. The tick checks: `now - agent.last_heartbeat_at >= agent.heartbeat_interval_seconds`.

---

## 8. Celery Task

```python
@celery_app.task(bind=True, max_retries=2)
def execute_agent_run(self, run_id: str):
    run = run_service.get(run_id)
    agent = agent_service.get(run.agent_id)
    adapter = adapter_registry.get(agent.adapter_type)

    run_service.update(run_id, status="running", started_at=utcnow())

    try:
        ctx = build_run_context(agent, run)
        result = adapter.execute(ctx)

        # Write transcript to disk
        transcript_path = write_transcript(agent, run, result)

        run_service.update(run_id,
            status="completed" if result.exit_code == 0 else "failed",
            finished_at=utcnow(),
            exit_code=result.exit_code,
            token_usage=result.token_usage,
            transcript_path=transcript_path,
            error_summary=result.error,
        )

    except Exception as e:
        run_service.update(run_id,
            status="failed",
            finished_at=utcnow(),
            error_summary=str(e),
        )
        raise self.retry(exc=e)
```

---

## 9. Auth Model

### 9.1 API Keys (human/external callers)

- API keys are org-scoped. Each key has a set of scopes.
- Keys are stored as bcrypt hashes. The raw key is shown once at creation.
- Format: `gw_live_<random>` (easy to grep in logs, easy to revoke).
- Middleware extracts the key from `Authorization: Bearer <key>`, looks up the hash, resolves the org, and attaches both to the request context.

### 9.2 Agent Runtime Tokens (injected at execution time)

When the gateway dispatches an agent run via Celery, the adapter injects these environment variables into the agent's process:

```
GATEWAY_URL=https://gateway.example.com/api/v1
GATEWAY_AGENT_TOKEN=eyJhbG...    # short-lived JWT (scoped to run duration)
GATEWAY_AGENT_ID=550e8400-...    # agent UUID
GATEWAY_AGENT_SLUG=dev-agent
GATEWAY_ORG_SLUG=acme
GATEWAY_RUN_ID=run-uuid
```

**JWT claims:**
```json
{
  "sub": "agent:550e8400-...",
  "org_id": "7c9e6679-...",
  "run_id": "run-uuid",
  "scopes": ["agents:read", "runs:read:own"],
  "exp": 1743800400
}
```

**Key design rules:**
- Tokens are short-lived (TTL = run timeout + buffer, e.g. 700s for a 600s timeout).
- Scopes are read-only by default: an agent can discover other agents in its org (`agents:read`) and read its own run status (`runs:read:own`), but cannot modify other agents or trigger runs.
- The org's master API key is **never** exposed to agent runtimes.
- No credentials are stored on disk (in `gateway.json` or elsewhere). Auth is always ephemeral and per-run.
- Future: expand scopes for agent callbacks (`runs:write:own`, `agents:delegate`).

---

## 10. Open Questions

These are decisions to revisit as you build:

1. **Session persistence across heartbeats.** Should an agent resume the same Claude Code session across heartbeat runs (like Paperclip does), or start fresh each time? Session reuse saves context/tokens but adds complexity.
2. **Agent-to-agent communication.** Collaborations handle the structured case. Are there scenarios where agents need ad-hoc 1:1 communication outside a collaboration?
3. **HEARTBEAT_OK suppression.** Like OpenClaw, if the agent reviews its checklist and finds nothing to do, should the gateway silently drop the response (no transcript, no run record)?
4. **File watching.** Should the gateway watch agent dirs for external edits (e.g., you edit SOUL.md in your editor) and reflect changes, or is the API the only write path?
5. **Run timeouts.** What's the default timeout for a run? Paperclip uses 600s. OpenClaw uses configurable per-agent timeouts.
6. **Adapter config secrets.** API keys for Anthropic, OpenAI etc. — should these live in adapter_config (encrypted JSONB), env vars, or a separate secrets store?
7. **gateway.json mutation policy.** Should agents be allowed to modify their own `gateway.json` (e.g., update skills, status)? For now unrestricted, but may need guardrails later to prevent agents from escalating their own capabilities.
8. **Collaboration context window management.** As group chat messages accumulate over many rounds, the context passed to each agent grows. Should there be a compaction/summarization step after N messages?
9. **Human-in-the-loop for collaborations.** Should a human be able to post a message into an active collaboration (e.g., course-correct mid-discussion)?

---

## 11. Future Considerations (not built now)

- **Agent callbacks (write)** — Expand agent JWT scopes so agents can update their own run status, write to memory, or delegate tasks to other agents
- **Channel routing** — Telegram/Slack/Discord → agent dispatch
- **WebSocket streaming** — Live run output for dashboard UI
- **Projects** — Work item grouping within an org
- **Cost budgets** — Monthly token budget per agent with auto-pause
- **Session persistence** — Carry context across heartbeat runs

---

## 12. Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transport | REST API | Simple, stateless, easy to test. WS later for streaming. |
| Agent identity | Markdown files on disk | Inspectable, git-friendly, OpenClaw-proven pattern. |
| Agent registry | SQLAlchemy (DB-agnostic) | Queryable metadata. SQLite dev, Postgres prod. |
| Run results | Hybrid (DB + filesystem) | DB for metadata queries, filesystem for full transcripts. |
| Execution | Celery + Redis | Async, concurrent, retryable, decoupled from gateway. |
| Heartbeat | Internal APScheduler | Gateway owns the loop. No external cron. |
| Auth | API key with scopes | Simple, org-scoped, production-ready from day one. |
| Multi-tenancy | Organization-scoped | All entities belong to an org. One deployment, many teams. |
| Adapters | Pluggable ABC | Runtime-agnostic. New runtimes don't touch core. |
| Templates | Jinja2 on disk | Agent scaffolding from templates at creation time. |
| Agent identity bridging | gateway.json + slug/UUID dual lookup | Filesystem stays human-readable, API stays programmatic. |
| Agent auth at runtime | Short-lived JWT via env vars | Agents can discover peers without exposing org API keys. |
| Multi-agent collaboration | Group chat + Celery-driven round-robin | Gateway orchestrates turns, agents only see shared messages. |

---

## 13. Collaborations (Multi-Agent Group Chat)

### 13.1 Concept

A collaboration is a shared conversation thread where multiple agents take turns solving a problem together. The lead agent (who received the original task) creates the group, and the gateway orchestrates a round-robin execution loop. Each agent sees only the group chat messages plus its own identity files — never the internal reasoning of other agents.

This is the gateway's core differentiator: **structured multi-agent reasoning through a shared message board, orchestrated as a single Celery task.**

### 13.2 Data Model

```
collaborations
  id              UUID PK
  org_id          UUID FK → organizations
  lead_agent_id   UUID FK → agents           -- the agent that created this
  source_run_id   UUID FK → runs NULL        -- the original run that spawned this
  title           VARCHAR                     -- human-readable description
  status          ENUM                        -- active, resolved, max_rounds_reached, failed, cancelled
  max_rounds      INT DEFAULT 10             -- safety limit
  routing_strategy VARCHAR DEFAULT 'round_robin'  -- round_robin, lead_directed, llm_orchestrated
  current_round   INT DEFAULT 0
  resolve_summary TEXT NULL                   -- lead agent's final summary
  celery_task_id  VARCHAR NULL               -- the group-run task
  created_at      TIMESTAMP
  finished_at     TIMESTAMP NULL

collaboration_members
  id              UUID PK
  collaboration_id UUID FK → collaborations
  agent_id        UUID FK → agents
  role            ENUM                        -- lead, member
  turn_order      INT                         -- 0, 1, 2... determines round-robin position
  joined_at       TIMESTAMP

collaboration_messages
  id              UUID PK
  collaboration_id UUID FK → collaborations
  agent_id        UUID FK → agents           -- who posted this
  run_id          UUID FK → runs NULL        -- the agent sub-run that produced this
  round           INT                         -- which round this message belongs to
  content         TEXT                        -- the distilled result posted to the group
  message_type    ENUM                        -- contribution, resolve, error
  created_at      TIMESTAMP
```

### 13.3 Execution Flow

```
POST /collaborations
  Body: {
    agent_ids: ["uuid-A", "uuid-B", "uuid-C"],  -- A is lead (first in list)
    title: "Implement auth module",
    message: "We need to build JWT auth. I need PM specs and security research.",
    max_rounds: 10,
    routing_strategy: "round_robin"              -- future: "lead_directed", "llm_orchestrated"
  }
      │
      ▼
Gateway:
  1. Creates collaboration record (status: active)
  2. Creates collaboration_members (A=lead/turn_0, B=member/turn_1, C=member/turn_2)
  3. Saves initial message from lead agent
  4. Dispatches Celery task: execute_group_run(collaboration_id)
      │
      ▼
Celery task: execute_group_run
  │
  │  members = [A (lead), B, C]   -- ordered by turn_order
  │  turn = 0
  │  max_turns = max_rounds * len(members)  -- e.g. 10 rounds × 3 agents = 30 turns
  │
  │  LOOP:
  │  while turn < max_turns:
  │      agent = get_next_agent(members, turn, messages, strategy)
  │      │
  │      │  1. Load group context:
  │      │     - All collaboration_messages so far (shared thread)
  │      │     - Agent's own SOUL.md, AGENTS.md (private identity)
  │      │     - Collaboration metadata (title, members, round number)
  │      │
  │      │  2. Build prompt:
  │      │     "You are {agent.name} in a group collaboration.
  │      │      Your role: {from SOUL.md}
  │      │      The team is working on: {title}
  │      │      Here is the conversation so far:
  │      │      ---
  │      │      [Agent A]: {message}
  │      │      [Agent B]: {message}
  │      │      ---
  │      │      Post your contribution. Be concise — share results, not process.
  │      │      {if lead}: If the task is complete, respond with RESOLVE: {summary}"
  │      │
  │      │  3. Execute agent via adapter (creates a sub-run record)
  │      │
  │      │  4. Extract the agent's response → save as collaboration_message
  │      │
  │      │  5. Check for RESOLVE signal:
  │      │     if agent is lead AND "RESOLVE:" in response:
  │      │         → extract summary
  │      │         → mark collaboration as resolved
  │      │         → break out of loop
  │      │
  │      turn += 1
  │
  │  If loop exits without RESOLVE:
  │      → mark collaboration as max_rounds_reached
  │      → optionally run lead agent one final time to summarize
```

### 13.4 Routing Strategy: get_next_agent

The turn order is controlled by a single function. The collaboration's `routing_strategy` field determines which implementation is used:

```python
def get_next_agent(
    members: list[CollaborationMember],
    current_turn: int,
    messages: list[CollaborationMessage],
    strategy: str,
) -> Agent:
    """Return the next agent to execute. This is the only place
    turn-order logic lives. The group-run loop never changes."""

    if strategy == "round_robin":
        # Simple rotation: A → B → C → A → B → C → ...
        return members[current_turn % len(members)]

    elif strategy == "lead_directed":
        # Lead agent's last message contains: NEXT: @agent-slug
        # Parse it and return that agent. Fall back to round-robin.
        ...

    elif strategy == "llm_orchestrated":
        # A lightweight LLM call reads the conversation and picks
        # who should speak next based on what's needed.
        ...

    else:
        return members[current_turn % len(members)]
```

**Why this matters:** The group-run Celery task is a simple `while` loop that calls `get_next_agent` — it doesn't know or care about the routing logic. Today it's round-robin. Tomorrow you can add an LLM orchestrator that skips agents when they're not needed, calls someone twice, or dynamically invites a new agent mid-collaboration. Same loop, different strategy.

### 13.4 REST API

```
POST   /collaborations                     Create and start a collaboration
  Body: { agent_ids, title, message, max_rounds? }

GET    /collaborations                     List collaborations
  Query: ?status=active&agent_id=...

GET    /collaborations/{id}                Get collaboration details + members + status

GET    /collaborations/{id}/messages       Get the group chat thread
  Query: ?round=3&limit=50

POST   /collaborations/{id}/cancel         Cancel an active collaboration

GET    /collaborations/{id}/runs           List all sub-runs (individual agent executions)
```

### 13.5 Context Isolation Model

```
┌─────────────────────────────────────────────┐
│           Collaboration Thread               │
│  (shared — all agents see this)              │
│                                              │
│  [Round 0]                                   │
│    Agent A (lead): "We need JWT auth..."     │
│    Agent B (PM): "Here are the specs..."     │
│    Agent C (researcher): "Security best..."  │
│                                              │
│  [Round 1]                                   │
│    Agent A: "Good. Let's refine..."          │
│    Agent B: "Updated acceptance criteria..." │
│    Agent C: "Found a vulnerability in..."    │
│                                              │
│  [Round 2]                                   │
│    Agent A: "RESOLVE: Final plan is..."      │
└─────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent A      │  │  Agent B      │  │  Agent C      │
│  (private)    │  │  (private)    │  │  (private)    │
│               │  │               │  │               │
│  SOUL.md      │  │  SOUL.md      │  │  SOUL.md      │
│  AGENTS.md    │  │  AGENTS.md    │  │  AGENTS.md    │
│  memory/      │  │  memory/      │  │  memory/      │
│  tools/       │  │  tools/       │  │  tools/       │
│               │  │               │  │               │
│  (full run    │  │  (full run    │  │  (full run    │
│   context     │  │   context     │  │   context     │
│   NOT shared) │  │   NOT shared) │  │   NOT shared) │
└──────────────┘  └──────────────┘  └──────────────┘
```

Each agent's adapter receives:
- **Shared context**: collaboration_messages (the group thread)
- **Private context**: agent's own SOUL.md, AGENTS.md, memory/, gateway.json
- **Never shared**: the agent's full execution trace, internal tool calls, stderr, reasoning

The agent posts only its **distilled contribution** to the group thread. The gateway extracts this from the adapter's RunResult.stdout.

### 13.6 Celery Task (pseudocode)

```python
@celery_app.task(bind=True)
def execute_group_run(self, collaboration_id: str):
    collab = collaboration_service.get(collaboration_id)
    members = collaboration_service.get_members_ordered(collaboration_id)
    max_turns = collab.max_rounds * len(members)
    turn = 0

    while turn < max_turns:
        messages = collaboration_service.get_messages(collaboration_id)

        # Single abstraction point for turn order
        member = get_next_agent(members, turn, messages, collab.routing_strategy)
        agent = agent_service.get(member.agent_id)
        adapter = adapter_registry.get(agent.adapter_type)
        round_num = turn // len(members)

        collaboration_service.update(collaboration_id, current_round=round_num)

        # Build prompt with group context + agent identity
        prompt = build_collaboration_prompt(
            agent=agent,
            messages=messages,
            collaboration=collab,
            is_lead=(member.role == "lead"),
            round_num=round_num,
        )

        # Create individual agent run record
        sub_run = run_service.create_run(
            agent_id=agent.id,
            trigger="collaboration",
            collaboration_id=collaboration_id,
            status="running",
        )

        try:
            ctx = build_run_context(agent, sub_run, message=prompt)
            result = adapter.execute(ctx)

            # Save the agent's contribution to the group thread
            contribution = extract_contribution(result.stdout)
            collaboration_service.add_message(
                collaboration_id=collaboration_id,
                agent_id=agent.id,
                run_id=sub_run.id,
                round=round_num,
                content=contribution,
                message_type="contribution",
            )

            # Save individual run record
            write_transcript(agent, sub_run, result)
            run_service.update(sub_run.id,
                status="completed",
                finished_at=utcnow(),
                token_usage=result.token_usage,
            )

            # Check for RESOLVE from lead agent
            if member.role == "lead" and is_resolve_signal(contribution):
                summary = extract_resolve_summary(contribution)
                collaboration_service.update(collaboration_id,
                    status="resolved",
                    resolve_summary=summary,
                    finished_at=utcnow(),
                )
                return  # Done!

        except Exception as e:
            collaboration_service.add_message(
                collaboration_id=collaboration_id,
                agent_id=agent.id,
                round=round_num,
                content=f"Agent error: {str(e)}",
                message_type="error",
            )
            run_service.update(sub_run.id, status="failed", error_summary=str(e))
            # Continue to next agent — don't fail the whole collaboration

        turn += 1

    # Max turns reached without resolution
    collaboration_service.update(collaboration_id,
        status="max_rounds_reached",
        finished_at=utcnow(),
    )
```

### 13.7 Relationship to Runs

A collaboration creates multiple individual runs:

```
collaboration (id: collab-1, status: resolved)
  ├── run (agent A, round 0, trigger: collaboration)
  ├── run (agent B, round 0, trigger: collaboration)
  ├── run (agent C, round 0, trigger: collaboration)
  ├── run (agent A, round 1, trigger: collaboration)
  ├── run (agent B, round 1, trigger: collaboration)
  ├── run (agent C, round 1, trigger: collaboration)
  └── run (agent A, round 2, trigger: collaboration)  ← resolved here
```

The `runs` table gets a new optional FK:

```
runs
  ...existing columns...
  collaboration_id  UUID FK → collaborations NULL  -- set for collaboration sub-runs
```
