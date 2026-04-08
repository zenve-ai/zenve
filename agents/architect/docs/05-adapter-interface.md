# Chunk 05 — Adapter Interface

## Goal
Define the BaseAdapter ABC, RunContext/RunResult dataclasses, and the AdapterRegistry. This is the pluggable execution layer.

## Depends On
- Chunk 04 (Agents — adapters execute agents)

## Referenced By
- Chunk 06 — Claude Code Adapter (first concrete adapter)
- Chunk 07 — Celery Setup & Run Execution (uses RunContext, RunResult, AdapterRegistry)
- Chunk 15 — Run Event System (adds `on_event` callback to RunContext)

## Deliverables

### 1. Data Models — `models/adapter.py`

#### Typed Adapter Config Models

```python
from pydantic import BaseModel

class AdapterConfigBase(BaseModel):
    """Base class for all adapter config models."""
    model_config = {"extra": "allow"}

class ClaudeCodeConfig(AdapterConfigBase):
    model: str | None = None            # optional, default: CLI default
    max_tokens: int | None = None       # optional
    max_turns: int | None = None        # optional
    # Note: tool permissions live in gateway.json, not adapter config

class CodexConfig(AdapterConfigBase):
    model: str | None = None            # optional
    max_tokens: int | None = None       # optional

class AnthropicAPIConfig(AdapterConfigBase):
    model: str = "claude-sonnet-4-6"   # required, defaulted
    max_tokens: int = 4096             # required, defaulted
    api_key_env_var: str = "ANTHROPIC_API_KEY"  # env var name for API key
```

#### RunContext and RunResult

```python
from dataclasses import dataclass

@dataclass
class RunContext:
    agent_dir: str              # absolute path to agent dir
    agent_id: str               # UUID from DB
    agent_slug: str
    agent_name: str
    org_id: str
    org_slug: str
    run_id: str
    adapter_type: str           # e.g. "claude_code", "codex"
    message: str | None         # user message for manual runs
    heartbeat: bool             # True if triggered by heartbeat
    adapter_config: dict        # adapter-specific config from DB (merged with defaults)
    gateway_url: str            # injected as env var
    agent_token: str            # short-lived JWT (Chunk 09, empty string for now)
    tools: list[str] | None     # from gateway.json; None = all tools allowed
    env_vars: dict              # extra env vars to pass

@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    token_usage: dict | None    # {input_tokens, output_tokens, cost_usd}
    duration_seconds: float
    error: str | None
```

### 2. Base Adapter — `agents/base.py`

```python
from abc import ABC, abstractmethod
from typing import ClassVar

class BaseAdapter(ABC):

    adapter_type: ClassVar[str]  # concrete subclasses declare this (e.g. "claude_code")

    def name(self) -> str:
        """Adapter identifier — reads adapter_type class variable."""
        return self.adapter_type

    @classmethod
    @abstractmethod
    def get_default_config(cls) -> AdapterConfigBase:
        """Return a default config instance for this adapter type."""
        ...

    @classmethod
    @abstractmethod
    def validate_config(cls, raw_config: dict) -> AdapterConfigBase:
        """Validate and coerce raw adapter_config dict into the typed config model."""
        ...

    @abstractmethod
    async def execute(self, ctx: RunContext) -> RunResult:
        """Execute the agent. Called inside a Celery worker."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the runtime is available (e.g., CLI installed)."""
        ...
```

### 3. Adapter Registry — `agents/registry.py`

```python
class AdapterRegistry:
    _adapters: dict[str, BaseAdapter]

    def __init__(self):
        self._adapters = {}

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.name()] = adapter

    def get(self, adapter_type: str) -> BaseAdapter:
        if adapter_type not in self._adapters:
            raise ValueError(f"Unknown adapter: {adapter_type}")
        return self._adapters[adapter_type]

    def has(self, adapter_type: str) -> bool:
        """Return True if adapter_type is registered."""
        return adapter_type in self._adapters

    def known_types(self) -> list[str]:
        """Return sorted list of all registered adapter type strings."""
        return sorted(self._adapters.keys())

    def list_adapters(self) -> list[str]:
        return list(self._adapters.keys())

    async def health_check_all(self) -> dict[str, bool]:
        return {
            name: await adapter.health_check()
            for name, adapter in self._adapters.items()
        }
```

### 4. Registry Initialization — `api/lifespan.py`

During app startup, create the registry and register available adapters:

```python
adapter_registry = AdapterRegistry()
# adapter_registry.register(ClaudeCodeAdapter())  # Chunk 06
# adapter_registry.register(CodexAdapter())        # future
```

Store on `app.state.adapter_registry` for access in routes/services.

### 5. RunContext Builder — `services/run_context.py`

`adapter_type` is passed in from the caller (resolved from `agent.adapter_type` in the DB). `adapter_config` is expected to be the already-merged config (defaults + stored overrides) by the time this builder is called.

```python
def build_run_context(
    agent: Agent,
    run: Run,
    adapter_registry: AdapterRegistry,
    message: str | None = None,
) -> RunContext:
    """Build a RunContext from DB models. Used by Celery tasks."""
    org = agent.organization
    adapter = adapter_registry.get(agent.adapter_type)
    default_cfg = adapter.get_default_config().model_dump()
    merged_cfg = {**default_cfg, **(agent.adapter_config or {})}

    # Read tool permissions from gateway.json
    gateway = filesystem.read_gateway_json(agent.dir_path)
    tools = gateway.get("tools")  # list[str] | None

    return RunContext(
        agent_dir=agent.dir_path,
        agent_id=str(agent.id),
        agent_slug=agent.slug,
        agent_name=agent.name,
        org_id=str(org.id),
        org_slug=org.slug,
        run_id=str(run.id),
        adapter_type=agent.adapter_type,
        message=message or run.message,
        heartbeat=(run.trigger == "heartbeat"),
        adapter_config=merged_cfg,
        gateway_url=settings.GATEWAY_URL,
        agent_token="",  # Populated in Chunk 09
        tools=tools,
        env_vars={},
    )
```

### 6. AgentService Integration — `services/agent.py`

`AgentService.__init__` accepts a third parameter `adapter_registry: AdapterRegistry`. The previous hard-coded `KNOWN_ADAPTER_TYPES` list check is replaced with registry-based validation. Default config is merged at agent-create time so stored `adapter_config` only contains user overrides.

```python
class AgentService:
    def __init__(self, db: Session, filesystem: FilesystemService, adapter_registry: AdapterRegistry):
        self.db = db
        self.filesystem = filesystem
        self.registry = adapter_registry

    def create_agent(self, org: Organization, data: AgentCreate) -> Agent:
        if not self.registry.has(data.adapter_type):
            raise ValueError(
                f"Unknown adapter type '{data.adapter_type}'. "
                f"Known types: {self.registry.known_types()}"
            )
        # Merge defaults with user-supplied config; store only what was supplied
        adapter = self.registry.get(data.adapter_type)
        adapter.validate_config(data.adapter_config or {})  # raises on invalid fields
        ...
```

The dependency function in `services/__init__.py` injects the registry from `app.state`:

```python
def get_agent_service(
    request: Request,
    db: Session = Depends(get_db),
    filesystem: FilesystemService = Depends(get_filesystem_service),
) -> AgentService:
    return AgentService(db, filesystem, request.app.state.adapter_registry)
```

## Notes
- The adapter interface is async (`async def execute`) to support both subprocess-based (Claude Code, Codex) and API-based (Anthropic API) adapters.
- `agents/` directory is used for adapters, not for agent CRUD logic (that's in `services/`).
- The registry is a singleton created at startup and passed via app state or dependency injection.
- `agent_token` is an empty string placeholder until Chunk 09 (Agent Runtime Tokens).
- `adapter_type` on `RunContext` is redundant with `adapter_config` contents but kept for clarity — Celery tasks resolve the adapter by type before building context.
- `validate_config()` raises a `ValidationError` (Pydantic) on invalid input; callers should catch and surface as HTTP 422.

## Change Log

| Date       | Change                                                                                     |
|------------|--------------------------------------------------------------------------------------------|
| 2026-04-06 | Added `adapter_type: ClassVar[str]` to `BaseAdapter`; `name()` made concrete               |
| 2026-04-06 | Added `get_default_config()` and `validate_config()` abstract classmethods to `BaseAdapter` |
| 2026-04-06 | Added `has()` and `known_types()` to `AdapterRegistry`                                     |
| 2026-04-06 | Added typed config models: `AdapterConfigBase`, `ClaudeCodeConfig`, `CodexConfig`, `AnthropicAPIConfig` |
| 2026-04-06 | Added `adapter_type: str` field to `RunContext`                                            |
| 2026-04-06 | Updated `RunContext` builder to accept `adapter_registry` and merge default config          |
| 2026-04-06 | Added `AgentService` integration section: registry param, `has()`/`known_types()` validation, dependency function |
| 2026-04-08 | Added `tools: list[str] | None` to `RunContext`; removed `allowed_tools` from `ClaudeCodeConfig` — tool permissions are agent-level (gateway.json), not adapter-level |
| 2026-04-08 | Updated `build_run_context` to read `tools` from `gateway.json` via `FilesystemService` |
