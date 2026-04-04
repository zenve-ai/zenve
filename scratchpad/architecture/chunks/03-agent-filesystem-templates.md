# Chunk 03 — Agent Filesystem & Templates

## Goal
Implement the agent directory structure and Jinja2 template scaffolding system. When an agent is created, the gateway scaffolds its identity files on disk.

## Depends On
- Chunk 01 (Organizations — for base_path)

## Deliverables

### 1. Template Directory — `/data/templates/default/`

Create default Jinja2 templates:

```
/data/templates/
  default/
    SOUL.md.j2
    AGENTS.md.j2
    HEARTBEAT.md.j2
    TOOLS.md.j2
```

Template variables available:
- `{{ agent_name }}` — human-readable name
- `{{ agent_slug }}` — URL-safe slug
- `{{ org_name }}` — organization name
- `{{ org_slug }}` — organization slug
- `{{ role }}` — optional role description (from creation request)
- `{{ adapter_type }}` — "claude_code", "codex", etc.

Example `SOUL.md.j2`:
```markdown
# {{ agent_name }}

You are **{{ agent_name }}**, an AI agent in the **{{ org_name }}** organization.

{% if role %}
## Role
{{ role }}
{% endif %}

## Identity
- Organization: {{ org_name }}
- Adapter: {{ adapter_type }}
```

### 2. Filesystem Service — `services/filesystem.py`

```python
class FilesystemService:
    def __init__(self, settings: Settings): ...

    def scaffold_agent_dir(
        self,
        org_slug: str,
        agent_slug: str,
        base_path: str,
        template_name: str,
        template_vars: dict,
    ) -> str:
        """
        Create agent directory structure and render templates.
        Returns the absolute path to the agent directory.

        Creates:
          {base_path}/agents/{agent_slug}/
            gateway.json
            SOUL.md
            AGENTS.md
            HEARTBEAT.md
            TOOLS.md
            memory/
              long_term.md
              scratch.md
            runs/
        """

    def write_gateway_json(self, agent_dir: str, data: dict) -> None:
        """Write/update gateway.json in the agent directory."""

    def read_agent_file(self, agent_dir: str, file_path: str) -> str:
        """Read a file from the agent directory. Validate path stays within agent_dir."""

    def write_agent_file(self, agent_dir: str, file_path: str, content: str) -> None:
        """Write a file to the agent directory. Validate path stays within agent_dir."""

    def list_agent_files(self, agent_dir: str) -> list[str]:
        """List all files in the agent directory (relative paths)."""

    def ensure_org_dir(self, base_path: str) -> None:
        """Create org directory structure if it doesn't exist."""
```

### 3. gateway.json Schema

Written at scaffold time, updated on agent config changes:

```json
{
  "id": "uuid",
  "slug": "dev-agent",
  "org_id": "uuid",
  "org_slug": "acme",
  "adapter_type": "claude_code",
  "skills": ["code_review", "testing"],
  "status": "active",
  "gateway_url": "https://gateway.example.com/api/v1",
  "created_at": "2026-04-04T12:00:00Z"
}
```

### 4. Config Addition — `config/settings.py`

```python
DATA_DIR: str = "/data"                  # root for all org/agent data
TEMPLATES_DIR: str = "/data/templates"   # where templates live
GATEWAY_URL: str = "http://localhost:8000/api/v1"
```

### 5. Path Security

All file read/write operations MUST validate that the resolved path stays within the agent's directory. Prevent path traversal attacks:

```python
def _validate_path(self, agent_dir: str, file_path: str) -> str:
    resolved = Path(agent_dir, file_path).resolve()
    if not str(resolved).startswith(str(Path(agent_dir).resolve())):
        raise ValueError("Path traversal detected")
    return str(resolved)
```

## Notes
- Templates are on disk, not in the database. Easy to customize per deployment.
- The `template` parameter in agent creation is optional — defaults to "default".
- `gateway.json` is the bridge between filesystem and API worlds.
- Memory files (`long_term.md`, `scratch.md`) are created empty at scaffold time.
- No credentials are ever stored in `gateway.json` or on disk.
