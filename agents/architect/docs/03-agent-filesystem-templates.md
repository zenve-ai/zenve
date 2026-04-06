# Chunk 03 — Agent Filesystem & Templates

## Goal
Define the agent directory structure and Jinja2 template scaffolding system. When an agent is created, the gateway renders these templates and writes the resulting files to disk. The templates establish an agent's identity, operational instructions, heartbeat behaviour, and tool constraints — all as human-readable markdown that the agent runtime reads at startup.

## Depends On
- Chunk 01 — Organizations (for `base_path`, `org_slug`, `org_name`)

## Referenced By
- Chunk 04 — Agents CRUD (calls `FilesystemService.scaffold_agent_dir` at creation time)
- Chunk 06 — Claude Code Adapter (reads SOUL.md, AGENTS.md, HEARTBEAT.md at run start)
- Chunk 10 — Heartbeat Scheduler (reads HEARTBEAT.md to drive tick behaviour)

---

## Deliverables

### 1. Template Directory Layout

Templates live under `TEMPLATES_DIR` (default `/data/templates`). Each named subdirectory is a template set. On creation the caller may specify `template: "default"` (or omit it); the gateway falls back to `"default"` if the named set doesn't exist.

```
/data/templates/
  default/
    SOUL.md.j2
    AGENTS.md.j2
    HEARTBEAT.md.j2
    TOOLS.md.j2
```

Agent directory created at scaffold time:

```
{org.base_path}/agents/{agent_slug}/
  gateway.json          ← written from code, not a template
  SOUL.md               ← rendered from SOUL.md.j2
  AGENTS.md             ← rendered from AGENTS.md.j2
  HEARTBEAT.md          ← rendered from HEARTBEAT.md.j2
  TOOLS.md              ← rendered from TOOLS.md.j2
  memory/
    long_term.md        ← empty stub
    scratch.md          ← empty stub
  runs/                 ← empty directory; run transcripts go here
```

---

### 2. Template Variables

All four templates share the same variable set:

| Variable | Type | Description |
|----------|------|-------------|
| `agent_name` | str | Human-readable display name |
| `agent_slug` | str | URL-safe slug used in paths and API |
| `org_name` | str | Organization display name |
| `org_slug` | str | Organization slug |
| `role` | str \| None | Optional role description from creation request |
| `adapter_type` | str | Runtime identifier: `"claude_code"`, `"codex"`, etc. |
| `gateway_url` | str | Base URL of the gateway API |
| `created_at` | str | ISO-8601 timestamp of agent creation |

---

### 3. `SOUL.md.j2` — Agent Identity

This is the agent's core identity file. The runtime injects it as the system prompt (or leading context) at the start of every run.

```markdown
# {{ agent_name }}

You are **{{ agent_name }}**, an AI agent operating inside the **{{ org_name }}** organization.
{% if role %}

## Role

{{ role }}
{% endif %}

## Identity

| Property | Value |
|----------|-------|
| Slug | `{{ agent_slug }}` |
| Organization | {{ org_name }} (`{{ org_slug }}`) |
| Runtime | {{ adapter_type }} |
| Created | {{ created_at }} |

## Core Directives

1. You act on behalf of the **{{ org_name }}** organization.
2. You follow the instructions in `AGENTS.md` for how to behave during a run.
3. You follow the instructions in `HEARTBEAT.md` for autonomous scheduled behaviour.
4. You respect the tool constraints defined in `TOOLS.md`.
5. You do not take actions outside the scope of your role.
6. When in doubt, do less and report back rather than acting unilaterally.

## Memory

- **Long-term memory** — persisted facts and decisions: `memory/long_term.md`
- **Scratch memory** — ephemeral working notes (cleared between runs): `memory/scratch.md`

Read both files at the start of each run. Write useful observations back before finishing.
```

---

### 4. `AGENTS.md.j2` — Run Instructions

This file drives how the agent behaves during an explicitly triggered run (via the Runs API). The runtime reads it once per run invocation.

```markdown
# {{ agent_name }} — Run Instructions

These instructions govern how you behave when the gateway invokes a run.

## On Start

1. Read `SOUL.md` — internalize your identity and role.
2. Read `memory/long_term.md` — load any persisted context.
3. Read `memory/scratch.md` — load working notes from previous runs.
4. Read the run prompt (provided by the caller in the run request).

## Executing the Task

- Complete the task described in the run prompt.
- Stay within the tool permissions listed in `TOOLS.md`.
- Use `memory/scratch.md` for notes you need within this run only.
- Use `memory/long_term.md` for facts worth keeping across runs.

## On Finish

Before ending the session:

1. Update `memory/long_term.md` with any durable observations.
2. Clear `memory/scratch.md` or leave a brief summary for the next run.
3. Produce a final response that the gateway will store as the run result.

## Signalling Outcomes

End your response with one of these signal lines so the gateway can parse the outcome:

| Signal | Meaning |
|--------|---------|
| `RUN_OK` | Task completed successfully |
| `RUN_FAILED: <reason>` | Task failed; include a short reason |
| `RUN_NEEDS_INPUT: <question>` | Blocked; waiting for more information |

## Gateway API

The gateway is reachable at `{{ gateway_url }}`. Your organization slug is `{{ org_slug }}`.
You may call the API using the JWT token injected in the `ZENVE_TOKEN` environment variable.
```

---

### 5. `HEARTBEAT.md.j2` — Autonomous Scheduled Behaviour

This file is read by the heartbeat scheduler (APScheduler) and injected into the run context for scheduled ticks. It defines what the agent should do when invoked autonomously on a timer.

```markdown
# {{ agent_name }} — Heartbeat Instructions

These instructions govern your behaviour during a scheduled heartbeat tick.
A heartbeat is an autonomous, timer-driven invocation — no caller prompt is provided.

## Purpose

Describe what this agent should do autonomously. Replace this section with
the agent's recurring responsibilities. Examples:

- Monitor a queue and process pending items
- Check for new data and summarise findings
- Run maintenance tasks on a schedule

## On Each Tick

1. Read `memory/long_term.md` — load persisted context.
2. Assess the current state: is there work to do?
3. If yes: perform the work and write results to `memory/long_term.md`.
4. If no: do nothing and signal `HEARTBEAT_OK` with a brief status note.

## Signalling Outcomes

End each heartbeat run with one of these signals:

| Signal | Meaning |
|--------|---------|
| `HEARTBEAT_OK` | Tick completed; nothing blocking |
| `HEARTBEAT_OK: <note>` | Tick completed; brief status |
| `HEARTBEAT_FAILED: <reason>` | Tick failed; needs attention |
| `HEARTBEAT_NEEDS_INPUT: <question>` | Blocked; cannot proceed autonomously |

## Constraints

- Heartbeat runs have a hard timeout (set by the gateway).
- Do not start long-running processes that outlive the tick.
- Do not prompt for user input — you are running unattended.

## Gateway API

The gateway is reachable at `{{ gateway_url }}`. Your organization slug is `{{ org_slug }}`.
Your JWT token is in the `ZENVE_TOKEN` environment variable.
```

---

### 6. `TOOLS.md.j2` — Tool Permissions

This file declares which tools and capabilities the agent is allowed to use. The runtime enforces these constraints (for adapters that support MCP permission flags or tool allow-lists).

```markdown
# {{ agent_name }} — Tool Permissions

This file defines the tools and capabilities available to this agent.
The runtime enforces these constraints. Do not attempt to use tools not listed here.

## Allowed Tools

Edit this section to list the specific tools granted to this agent.
Use MCP server names, CLI tool names, or capability categories as appropriate.

    # Example — replace with actual tool grants:
    # mcp__filesystem__read_file
    # mcp__filesystem__write_file
    # Bash (read-only, no network)

## Disallowed Actions

Unless explicitly listed above, the following are always prohibited:

- Accessing filesystems outside `{{ agent_slug }}/` agent directory
- Making outbound network requests not via the gateway API
- Installing packages or modifying system configuration
- Reading or writing other agents' directories
- Storing credentials or secrets in any file

## Runtime: {{ adapter_type }}

Adapter-specific tool configuration may be set in `gateway.json`.
```

---

### 7. Memory File Stubs

Two empty markdown files are created at scaffold time. They are intentionally minimal.

**`memory/long_term.md`**
```markdown
# {{ agent_name }} — Long-Term Memory

This file persists facts, decisions, and context across runs.
Update it at the end of each run with anything worth keeping.

---

_No entries yet._
```

**`memory/scratch.md`**
```markdown
# {{ agent_name }} — Scratch Memory

This file holds ephemeral notes within a single run.
Clear or summarize it at the end of each run.

---

_Empty._
```

---

### 8. `gateway.json` Schema

Written programmatically at scaffold time (not a Jinja2 template). Updated whenever the agent's config changes via the API.

```json
{
  "id": "uuid",
  "slug": "dev-agent",
  "org_id": "uuid",
  "org_slug": "acme",
  "adapter_type": "claude_code",
  "skills": [],
  "status": "active",
  "heartbeat_interval_seconds": 0,
  "gateway_url": "https://gateway.example.com/api/v1",
  "created_at": "2026-04-04T12:00:00Z"
}
```

Fields:

| Field | Description |
|-------|-------------|
| `id` | Agent UUID (from DB) |
| `slug` | Agent slug (URL-safe) |
| `org_id` | Owning organization UUID |
| `org_slug` | Owning organization slug |
| `adapter_type` | Runtime adapter identifier |
| `skills` | Optional tags / capability hints |
| `status` | `active` \| `inactive` \| `archived` |
| `heartbeat_interval_seconds` | Heartbeat tick interval in seconds; `0` means disabled |
| `gateway_url` | Base URL agents use to call back home |
| `created_at` | ISO-8601 creation timestamp |

No secrets or credentials are stored here.

---

### 9. Filesystem Service — `services/filesystem.py`

```python
class FilesystemService:
    def __init__(self, settings: Settings): ...

    def scaffold_agent_dir(
        self,
        org_slug: str,
        agent_slug: str,
        base_path: str,
        template_vars: dict,
        template_name: str = "default",
    ) -> str:
        """
        Render templates and create the agent directory structure.
        Returns the absolute path to the created agent directory.
        Raises FileExistsError if the directory already exists.
        """

    def write_gateway_json(self, agent_dir: str, data: dict) -> None:
        """Write or overwrite gateway.json in the agent directory."""

    def read_gateway_json(self, agent_dir: str) -> dict:
        """Read and parse gateway.json from the agent directory."""

    def read_agent_file(self, agent_dir: str, file_path: str) -> str:
        """Read a file relative to agent_dir. Validates no path traversal."""

    def write_agent_file(self, agent_dir: str, file_path: str, content: str) -> None:
        """Write a file relative to agent_dir. Validates no path traversal."""

    def list_agent_files(self, agent_dir: str) -> list[str]:
        """Return relative paths of all files under agent_dir."""

    def ensure_org_dir(self, base_path: str) -> None:
        """Create {base_path}/agents/ if it does not exist."""

    def _validate_path(self, agent_dir: str, file_path: str) -> str:
        """
        Resolve file_path relative to agent_dir.
        Raise ValueError if the resolved path escapes agent_dir.
        """
```

---

### 10. Config Additions — `config/settings.py`

```python
DATA_DIR: str = "/data"                        # root for all org/agent data
TEMPLATES_DIR: str = "/data/templates"         # Jinja2 template sets
GATEWAY_URL: str = "http://localhost:8000/api/v1"
```

---

### 11. Bundled Templates & Bootstrap Seeding

#### Problem

On a fresh deployment `TEMPLATES_DIR` is empty — there are no templates to scaffold agents from. The templates must ship with the gateway release so the system is usable out of the box.

#### Solution: package data + startup seeding

**11a. Package layout**

The default template set is stored inside the Python package so it is included in the wheel and available at any path via `importlib.resources`:

```
src/zenve/
  templates/
    default/
      SOUL.md.j2
      AGENTS.md.j2
      HEARTBEAT.md.j2
      TOOLS.md.j2
```

`pyproject.toml` must declare these as package data so they are included in the built distribution:

```toml
[tool.setuptools.package-data]
"zenve" = ["templates/**/*.j2"]
```

**11b. Startup seeding in `api/lifespan.py`**

On gateway startup, `FilesystemService.seed_default_templates()` is called. It copies the bundled `default/` set to `TEMPLATES_DIR/default/` only if that directory does not already exist — preserving any customisations the operator has made.

```python
# api/lifespan.py  (inside the startup block)
filesystem_service.seed_default_templates()
```

```python
# services/filesystem.py
import importlib.resources
import shutil

class FilesystemService:
    ...

    def seed_default_templates(self) -> None:
        """
        Copy the bundled default template set to TEMPLATES_DIR/default/
        if it does not already exist on disk.
        Idempotent — safe to call on every startup.
        """
        dest = Path(self.settings.TEMPLATES_DIR) / "default"
        if dest.exists():
            return  # operator may have customised; never overwrite
        with importlib.resources.files("zenve.templates") as pkg_templates:
            shutil.copytree(str(pkg_templates / "default"), str(dest))
```

#### Behaviour summary

| Scenario | Result |
|----------|--------|
| Fresh deployment, empty `TEMPLATES_DIR` | Bundled defaults are seeded on first startup |
| Existing `TEMPLATES_DIR/default/` | Not touched — operator customisations preserved |
| Custom template set (e.g. `minimal/`) | Not affected; only `default/` is managed |
| Gateway upgrade (new template version) | Default set is **not** auto-updated; operator must delete `default/` to re-seed |

#### Upgrade path

If a gateway release ships updated default templates, operators who want the new defaults must delete `TEMPLATES_DIR/default/` before restarting. A future migration utility can handle this automatically, but is out of scope for this chunk.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Template format | Jinja2 | Standard Python templating; readable conditionals for optional fields |
| Template discovery | Named directories under `TEMPLATES_DIR` | Deployers can add custom sets without code changes |
| Bundled defaults | Package data in `src/zenve/templates/default/` | Ships with the wheel; no separate asset distribution needed |
| Seeding strategy | Copy-once on startup (skip if exists) | Idempotent; preserves operator customisations across restarts |
| Signal protocol | Plain text suffix (`RUN_OK`, `HEARTBEAT_OK`, etc.) | Simple to parse, works with any LLM output |
| Memory split | `long_term.md` + `scratch.md` | Separates durable facts from ephemeral notes; keeps long_term.md clean |
| `gateway.json` format | JSON (not template) | Programmatic writes are cleaner in JSON; no template needed |
| No credentials on disk | Enforced by policy in TOOLS.md | Secrets go in env vars (ZENVE_TOKEN), never in agent files |

## Notes

- The `role` variable is optional; templates use `{% if role %}` guards to avoid blank sections.
- The `runs/` directory is created empty. Run transcripts written here by adapters follow the naming convention `{run_id}.md` (defined in Chunk 08).
- `memory/scratch.md` clearing policy is advisory — the agent is responsible; the gateway does not truncate it.
- The signal protocol (`RUN_OK`, `HEARTBEAT_OK`, etc.) must be documented in AGENTS.md and HEARTBEAT.md consistently. The adapter parser (Chunk 06) and heartbeat service (Chunk 10) depend on these exact strings.
- Custom template sets inherit no defaults from `default/` — each set must provide all four template files.
- `src/zenve/templates/` is never imported as Python — it is pure data. The `importlib.resources` API is used to locate it at runtime regardless of install method (editable, wheel, zip).

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-06 | Created chunk with full template designs for SOUL.md.j2, AGENTS.md.j2, HEARTBEAT.md.j2, TOOLS.md.j2, memory stubs, gateway.json schema, FilesystemService signature, and config additions | Initial design of agent file templates |
| 2026-04-06 | Added `heartbeat_interval_seconds` to gateway.json schema and field table; fixed nested code block in TOOLS.md.j2 section | Align gateway.json with ORM model (chunk 04); fix markdown rendering |
| 2026-04-06 | Added section 11: bundled templates & bootstrap seeding — package data layout, `seed_default_templates()`, behaviour table, upgrade path | Fresh deployments have empty TEMPLATES_DIR; defaults must ship with the gateway |
