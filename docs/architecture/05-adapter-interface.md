# Chunk 05 — Adapter Interface

## Goal
Define the `BaseAdapter` ABC, `RunContext`/`RunResult` dataclasses, and the `AdapterRegistry`. This is the pluggable execution layer — adapters live in the `zenve-adapters` package and are stateless singletons registered at startup.

## Depends On
- Chunk 04 — Agents CRUD (adapters execute agents; `AgentService` validates adapter type against registry)

## Referenced By
- Chunk 06 — Concrete Adapters (first implementations)
- Chunk 07 — Celery Setup & Run Execution (uses `RunContext`, `RunResult`, `AdapterRegistry`)
- Chunk 15 — Run Event System (`on_event` callback on `RunContext`)

---

## Deliverables

### 1. Package — `packages/adapters/`

```
packages/adapters/
  src/zenve_adapters/
    __init__.py      # exports BaseAdapter, AdapterRegistry
    base.py
    registry.py
    claude_code.py   # Chunk 06
    open_code.py     # Chunk 06
```

**Dependency chain:** `zenve-adapters` → `zenve-models` only.

---

### 2. Config Models — `models/adapter.py`

```python
class AdapterConfigBase(BaseModel):
    model_config = {"extra": "ignore"}   # unknown keys silently dropped

class ClaudeCodeConfig(AdapterConfigBase):
    model: str = "claude-sonnet-4-6"
    max_tokens: int | None = None
    max_turns: int = 10
    output_format: str = "stream-json"

class CodexConfig(AdapterConfigBase):
    model: str = "o4-mini"
    max_tokens: int | None = None
    approval_mode: str = "suggest"

class OpenCodeConfig(AdapterConfigBase):
    model: str = ""
    max_tokens: int | None = None
    steps: int = 10
    output_format: str = "json"

class AnthropicAPIConfig(AdapterConfigBase):
    model: str = "claude-opus-4-5"
    max_tokens: int = 4096
    temperature: float = 1.0
    system_prompt_override: str | None = None
```

---

### 3. RunContext and RunResult — `models/adapter.py`

```python
@dataclass
class RunContext:
    agent_dir: str
    agent_id: str
    agent_slug: str
    agent_name: str
    org_id: str
    org_slug: str
    run_id: str
    adapter_type: str
    adapter_config: dict
    message: str | None
    heartbeat: bool
    gateway_url: str
    agent_token: str                    # short-lived JWT (Chunk 09); empty string until then
    tools: list[str] | None = None      # None = all tools allowed
    env_vars: dict = field(default_factory=dict)
    on_event: Callable[[str, str | None, dict | None], None] = field(
        default=lambda *a, **kw: None   # no-op until Chunk 15 wires a real handler
    )

@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    token_usage: dict | None = None     # {input_tokens, output_tokens, cost_usd, ...}
    error: str | None = None
```

---

### 4. BaseAdapter — `packages/adapters/base.py`

```python
class BaseAdapter(ABC):
    """Stateless — one instance per adapter_type, created at startup, reused for all runs."""

    adapter_type: ClassVar[str]

    def name(self) -> str:
        return self.__class__.adapter_type

    @classmethod
    @abstractmethod
    def get_default_config(cls) -> AdapterConfigBase:
        """Return default config instance. Called by AgentService.create() to merge with user overrides."""
        ...

    @classmethod
    @abstractmethod
    def validate_config(cls, raw_config: dict) -> AdapterConfigBase:
        """Validate raw adapter_config dict. Raises pydantic.ValidationError on invalid input."""
        ...

    @abstractmethod
    async def execute(self, ctx: RunContext) -> RunResult:
        """Execute one agent run. Must NOT raise on non-zero subprocess exit — capture in RunResult.exit_code.
        Only raise for infrastructure failures that should trigger a Celery retry."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if runtime dependency is available. Must never raise."""
        ...
```

---

### 5. AdapterRegistry — `packages/adapters/registry.py`

```python
class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        """Raises ValueError if adapter_type already registered."""
        key = adapter.name()
        if key in self._adapters:
            raise ValueError(f"Adapter already registered: {key!r}")
        self._adapters[key] = adapter

    def get(self, adapter_type: str) -> BaseAdapter:
        """Raises KeyError if not registered. AgentService converts this to HTTP 422."""
        if adapter_type not in self._adapters:
            raise KeyError(f"Unknown adapter_type: {adapter_type!r}")
        return self._adapters[adapter_type]

    def has(self, adapter_type: str) -> bool: ...
    def known_types(self) -> list[str]: ...  # sorted

    async def health_check_all(self) -> dict[str, bool]:
        """Run health_check() on all adapters concurrently via asyncio.gather(return_exceptions=True)."""
        ...
```

---

### 6. Registry Initialization — `api/lifespan.py`

```python
adapter_registry = AdapterRegistry()
adapter_registry.register(ClaudeCodeAdapter())
adapter_registry.register(OpenCodeAdapter())
app.state.adapter_registry = adapter_registry
```

---

### 7. AgentService Integration — `services/agent.py`

`AgentService.__init__` receives the registry alongside other dependencies. The registry drives adapter validation at agent-create time.

```python
class AgentService:
    def __init__(
        self,
        db: Session,
        filesystem: FilesystemService,
        adapter_registry: AdapterRegistry,
        template_service: TemplateService,
        scaffolding: ScaffoldingService,
        preset_service: PresetService,
    ): ...

    def create(self, org: Organization, data: AgentCreate) -> Agent:
        if not self.adapter_registry.has(data.adapter_type):
            raise HTTPException(422, f"Unknown adapter_type '{data.adapter_type}'. Known: {self.adapter_registry.known_types()}")
        adapter = self.adapter_registry.get(data.adapter_type)
        default_config = adapter.get_default_config().model_dump(exclude_none=True)
        adapter_config = {**default_config, **data.adapter_config}
        ...
```

Dependency function in `services/__init__.py`:

```python
def get_agent_service(
    db: Session = Depends(get_db),
    filesystem: FilesystemService = Depends(get_filesystem_service),
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    template_service: TemplateService = Depends(get_template_service),
    scaffolding: ScaffoldingService = Depends(get_scaffolding_service),
    preset_service: PresetService = Depends(get_preset_service),
) -> AgentService:
    return AgentService(db, filesystem, adapter_registry, template_service, scaffolding, preset_service)

def get_adapter_registry(request: Request) -> AdapterRegistry:
    return request.app.state.adapter_registry
```

---

## Notes

- `AdapterConfigBase` uses `extra = "ignore"` — unknown fields are silently dropped. This prevents stale keys in stored configs from causing failures on upgrade.
- `on_event` defaults to a no-op lambda so adapters can call `ctx.on_event(...)` unconditionally even before Chunk 15 wires a real handler.
- `validate_config()` raises `pydantic.ValidationError`; callers surface as HTTP 422.
- `agent_token` is an empty string until Chunk 09. Adapters should inject it as `GATEWAY_AGENT_TOKEN` env var regardless.
- `health_check_all()` uses `return_exceptions=True` so one failing health check doesn't prevent others from running. Exceptions are treated as `False`.

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-06 | Created chunk: BaseAdapter, RunContext/RunResult, AdapterRegistry, config models | Initial design |
| 2026-04-06 | Added `get_default_config()`, `validate_config()`, `has()`, `known_types()` | Registry-based validation |
| 2026-04-08 | Added `tools: list[str] | None` to RunContext; removed `allowed_tools` from ClaudeCodeConfig | Tool permissions are agent-level |
| 2026-04-09 | Updated `build_run_context` to read `tools` from Agent DB model | Removed gateway.json |
| 2026-04-10 | Package renamed to `zenve-adapters` in `packages/adapters/`; `on_event` now a dataclass field with no-op default; `extra = "ignore"` on AdapterConfigBase; config models updated with real defaults (`output_format`, `approval_mode`, `temperature`, etc.); `OpenCodeConfig` added; `AdapterRegistry.register()` raises on duplicate; `get()` raises KeyError; `health_check_all()` uses asyncio.gather; `AgentService` constructor updated with full dependency list | Reflects implemented adapters package |
