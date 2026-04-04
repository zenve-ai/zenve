# Chunk 05 — Adapter Interface

## Goal
Define the BaseAdapter ABC, RunContext/RunResult dataclasses, and the AdapterRegistry. This is the pluggable execution layer.

## Depends On
- Chunk 04 (Agents — adapters execute agents)

## Deliverables

### 1. Data Models — `models/adapter.py`

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
    message: str | None         # user message for manual runs
    heartbeat: bool             # True if triggered by heartbeat
    adapter_config: dict        # adapter-specific config from DB
    gateway_url: str            # injected as env var
    agent_token: str            # short-lived JWT (Chunk 09, empty string for now)
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

```python
def build_run_context(agent: Agent, run: Run, message: str | None = None) -> RunContext:
    """Build a RunContext from DB models. Used by Celery tasks."""
    org = agent.organization
    return RunContext(
        agent_dir=agent.dir_path,
        agent_id=str(agent.id),
        agent_slug=agent.slug,
        agent_name=agent.name,
        org_id=str(org.id),
        org_slug=org.slug,
        run_id=str(run.id),
        message=message or run.message,
        heartbeat=(run.trigger == "heartbeat"),
        adapter_config=agent.adapter_config or {},
        gateway_url=settings.GATEWAY_URL,
        agent_token="",  # Populated in Chunk 09
        env_vars={},
    )
```

## Notes
- The adapter interface is async (`async def execute`) to support both subprocess-based (Claude Code, Codex) and API-based (Anthropic API) adapters.
- `agents/` directory is used for adapters, not for agent CRUD logic (that's in `services/`).
- The registry is a singleton created at startup and passed via app state or dependency injection.
- `agent_token` is an empty string placeholder until Chunk 09 (Agent Runtime Tokens).
