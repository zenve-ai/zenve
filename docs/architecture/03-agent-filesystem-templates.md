# Chunk 03 — Agent Filesystem & Templates

## Goal
Define the agent directory structure and Jinja2 template scaffolding system. When an agent is created, `ScaffoldingService` renders templates and writes the resulting files to disk. Templates establish an agent's identity, run instructions, and heartbeat behaviour. A separate preset system ships named YAML configurations that pre-fill agent creation fields — making it easy to spin up opinionated agent types. A `TemplateService` exposes templates and their variable manifests via REST so callers can discover what each template needs before creating an agent.

## Depends On
- Chunk 01 — Organizations (for `base_path`, `org_slug`, `org_name`)

## Referenced By
- Chunk 04 — Agents CRUD (calls `ScaffoldingService.scaffold_agent_dir` at creation time)
- Chunk 06 — Claude Code Adapter (reads SOUL.md, AGENTS.md, RUN.md, HEARTBEAT.md at run start)
- Chunk 10 — Heartbeat Scheduler (reads HEARTBEAT.md to drive tick behaviour)

---

## Deliverables

### 1. Package — `packages/scaffolding/`

Templates and preset management live in their own package `zenve-scaffolding`, not in `zenve-services`.

```
packages/scaffolding/
  src/zenve_scaffolding/
    scaffolding_service.py   # ScaffoldingService
    preset_service.py        # PresetService
    templates/
      default/
        manifest.json        # variable schema for this template set
        SOUL.md.j2
        AGENTS.md.j2
        RUN.md.j2
        HEARTBEAT.md.j2
    presets/
      architect.yaml
      dev.yaml
```

**Dependency chain:** `zenve-scaffolding` → `zenve-config`, `zenve-models`

Agent directory created at scaffold time:

```
{org.base_path}/agents/{agent_slug}/
  SOUL.md               ← identity, personality, workspace context
  AGENTS.md             ← task-specific instructions (injected via template_vars)
  RUN.md                ← run execution protocol (memory, signals, gateway URL)
  HEARTBEAT.md          ← autonomous tick instructions
  memory/
    long_term.md        ← empty stub
    scratch.md          ← empty stub
  runs/                 ← empty directory; run transcripts go here
```

---

### 2. Template Variables

All templates share these variables. Most are injected by the gateway at creation time; others come from the agent creation request or preset.

| Variable | Type | Source | Description |
|----------|------|--------|-------------|
| `agent_name` | str | DB | Human-readable display name |
| `agent_slug` | str | DB | URL-safe slug used in paths and API |
| `org_name` | str | Org | Organization display name |
| `org_slug` | str | Org | Organization slug |
| `org_dir` | str | Settings | Absolute path to org filesystem root |
| `gateway_url` | str | Settings | Base URL of the gateway API |
| `created_at` | str | DB | ISO-8601 timestamp of agent creation |
| `role` | str \| None | Request/preset | Optional role description |
| `personality` | str \| None | Request/preset | Personality traits (markdown list). Falls back to scoped/conservative defaults |
| `cares_about` | str \| None | Request/preset | What the agent cares about (markdown list). Falls back to org-aligned defaults |
| `does_not_do` | str \| None | Request/preset | Behavioural guardrails (markdown list). Falls back to safe defaults |
| `instructions` | str | Request/preset | Task instructions injected into AGENTS.md (**required** for default template) |

---

### 3. `SOUL.md.j2` — Agent Identity

Core identity file. The adapter injects it as system prompt or leading context at the start of every run.

Sections rendered:
- **Identity** — agent name, org, personality (custom or fallback defaults)
- **What you care about** — `cares_about` variable or org-aligned defaults
- **What you don't do** — `does_not_do` variable or safe defaults
- **Workspace** — explains `{org_dir}` layout with agents/, projects/; sets CWD expectation

---

### 4. `AGENTS.md.j2` — Task Instructions

Minimal injection point for task-specific instructions:

```
# You are {agent_name}

{{ instructions }}
```

The `instructions` variable is required by the `default` manifest. It is typically supplied by the preset or directly in the agent creation request.

---

### 5. `RUN.md.j2` — Run Execution Protocol

Contains the runtime execution contract: memory loading, task execution, finish behaviour, signal protocol, and gateway URL. This file is stable across templates and agents — presets do not override it.

```markdown
## Signalling Outcomes
| Signal | Meaning |
|--------|---------|
| `RUN_OK` | Task completed successfully |
| `RUN_FAILED: <reason>` | Task failed; include a short reason |
| `RUN_NEEDS_INPUT: <question>` | Blocked; waiting for more information |
```

---

### 6. `HEARTBEAT.md.j2` — Autonomous Scheduled Behaviour

Read by the heartbeat scheduler (Chunk 10). Contains a `## Tasks` section (empty stub by default — operators fill it in) and the tick protocol.

```markdown
## Signalling Outcomes
| Signal | Meaning |
|--------|---------|
| `HEARTBEAT_OK: nothing to do` | No tasks defined; tick skipped |
| `HEARTBEAT_OK: <note>` | Tasks completed; brief summary |
| `HEARTBEAT_FAILED: <reason>` | Tick failed; needs attention |
| `HEARTBEAT_NEEDS_INPUT: <question>` | Blocked; cannot proceed autonomously |
```

---

### 7. `manifest.json` — Template Variable Schema

Each template set ships a `manifest.json` declaring its name, description, and required variables:

```json
{
  "name": "default",
  "description": "General-purpose agent with configurable identity, personality, and behavioral guardrails.",
  "variables": [
    { "name": "instructions", "type": "string", "required": true, "description": "..." },
    { "name": "role",         "type": "string", "required": true,  "description": "..." },
    { "name": "personality",  "type": "string", "required": false, "description": "..." },
    { "name": "cares_about",  "type": "string", "required": false, "description": "..." },
    { "name": "does_not_do",  "type": "string", "required": false, "description": "..." }
  ]
}
```

`manifest.json` is always re-synced on gateway startup (even if the template directory already exists), so variable schema updates ship automatically without touching user-customised `.j2` files.

---

### 8. `ScaffoldingService` — `packages/scaffolding/`

```python
class ScaffoldingService:
    def __init__(self, settings: Settings) -> None: ...

    def scaffold_agent_dir(
        self,
        org_slug: str,
        agent_slug: str,
        base_path: str,
        template_vars: dict,
        template_name: str = "default",
    ) -> str:
        """Render templates and create agent directory. Returns absolute path.
        Raises FileExistsError if directory already exists.
        Falls back to 'default' if template_name directory is not found.
        """

    def seed_default_templates(self) -> None:
        """Copy bundled default template set to TEMPLATES_DIR/default/ if absent.
        Always re-syncs manifest.json. Idempotent — safe to call on every startup.
        """

    def copy_traversable(self, src: Traversable, dest: Path) -> None:
        """Recursively copy a package-data Traversable tree to a real filesystem path."""

    def write_memory_stub(self, path: Path, content: str) -> None:
        """Write a memory stub file."""
```

---

### 9. `TemplateService` — `packages/services/`

```python
class TemplateService:
    def list_templates(self) -> list[TemplateSummary]: ...
    def get_manifest(self, template_name: str) -> TemplateManifest: ...   # 404 if missing
    def validate_vars(self, template_name: str, template_vars: dict | None) -> None:
        """Raise HTTP 422 if any required manifest variables are missing."""
    def resolve_template_name(self, template_name: str) -> str:
        """Return template_name if it exists on disk, else 'default'."""
```

---

### 10. Preset System

Presets are named YAML files bundled inside `zenve_scaffolding/presets/`. Each preset is a complete agent configuration — callers load a preset and receive all fields needed to create an agent.

**Pydantic model — `models/preset.py`:**

```python
class Preset(BaseModel):
    name: str
    description: str = ""
    adapter_type: str = "claude_code"
    template: str = "default"
    template_vars: dict[str, str] = {}   # role, personality, cares_about, does_not_do, instructions
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = ["Read", "Write", "Bash"]
    heartbeat_interval_seconds: int = 0

class PresetSummary(BaseModel):
    name: str
    description: str = ""
```

**`PresetService` — `packages/scaffolding/`:**

```python
class PresetService:
    def list_presets(self) -> list[PresetSummary]: ...  # reads all .yaml from package data
    def load_preset(self, name: str) -> Preset: ...     # 404 if not found
```

**Bundled presets:**

| Preset | Adapter | Description |
|--------|---------|-------------|
| `architect` | `claude_code` | Software architect that maintains living architecture docs |
| `dev` | `open_code` | Python developer working on FastAPI backends |

---

### 11. Routes

**Templates — `api/routes/template.py`:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/templates` | List all available template sets |
| GET | `/api/v1/templates/{name}` | Get manifest (variable schema) for a template |

**Presets — `api/routes/preset.py`:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/presets` | List all bundled presets |
| GET | `/api/v1/presets/{name}` | Get full preset configuration |

Both routes are read-only and do not require API key auth — they expose static package data.

---

### 12. Config

```python
templates_dir: str = "/data/templates"   # Jinja2 template sets
data_dir: str = "/data"                  # root for all org/agent data
gateway_url: str = "http://localhost:8000/api/v1"
```

---

### 13. Startup Seeding

`ScaffoldingService.seed_default_templates()` is called from `api/lifespan.py` on every gateway startup:

| Scenario | Result |
|----------|--------|
| Fresh deployment, empty `TEMPLATES_DIR` | Bundled defaults seeded in full |
| Existing `TEMPLATES_DIR/default/` | `.j2` files untouched; `manifest.json` always re-synced |
| Custom template set (e.g. `minimal/`) | Not affected; only `default/` is managed |
| Gateway upgrade | Updated `manifest.json` applied automatically; `.j2` files preserved |

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dedicated package | `zenve-scaffolding` | Templates and presets are self-contained; separate from business-logic services |
| 4 template files | SOUL + AGENTS + RUN + HEARTBEAT | RUN.md isolates the execution protocol; AGENTS.md stays minimal for task injection |
| AGENTS.md as thin wrapper | `# You are {name}\n\n{{ instructions }}` | Task instructions are agent-specific and change often; separating them from identity keeps SOUL.md stable |
| manifest.json always synced | Re-written on every startup | Allows variable schema updates to ship without forcing operators to delete template dirs |
| Presets in package data | YAML files in `zenve_scaffolding/presets/` | Ships with the wheel; no DB needed; version-controlled alongside code |
| Preset model includes `tools` + `skills` | Full agent config in one payload | Callers load one preset and have everything needed to POST `/agents` |
| Template fallback | Unknown template → `default` | Prevents hard failures on misconfiguration |
| Signal protocol | Plain text suffix (`RUN_OK`, `HEARTBEAT_OK`, etc.) | Simple to parse; works with any LLM output |

## Notes

- The `instructions` variable is **required** by the default manifest. Agent creation will return HTTP 422 if it is missing and not supplied by a preset.
- `memory/scratch.md` clearing policy is advisory — the agent is responsible; the gateway does not truncate it.
- Custom template sets must provide all four `.j2` files (SOUL, AGENTS, RUN, HEARTBEAT). No inheritance from `default/`.
- The `runs/` directory is created empty. Transcript naming convention is defined in Chunk 08.
- `zenve_scaffolding/templates/` and `zenve_scaffolding/presets/` are never imported as Python — they are package data accessed via `importlib.resources`.

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-06 | Created chunk with template designs, FilesystemService signature, config additions | Initial design |
| 2026-04-06 | Added bundled templates & bootstrap seeding section | Fresh deployments need defaults shipped with gateway |
| 2026-04-08 | Removed TOOLS.md.j2; tool permissions stored on Agent DB model | Redundant with DB as source of truth |
| 2026-04-09 | Removed `gateway.json`; identity injected at runtime via system prompt and env vars | gateway.json was redundant with DB |
| 2026-04-10 | Major update: scaffolding extracted to `zenve-scaffolding` package; added RUN.md.j2; AGENTS.md.j2 simplified to instructions injection; added manifest.json per template set with always-sync seeding; added PresetService with YAML presets (architect, dev); added TemplateService with manifest validation; added /api/v1/templates and /api/v1/presets routes; expanded template variables (personality, cares_about, does_not_do, instructions, org_dir) | Reflects implemented scaffolding package with preset and template discovery APIs |
