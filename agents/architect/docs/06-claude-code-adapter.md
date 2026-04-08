# Chunk 06 — Claude Code Adapter

## Goal
Implement the first concrete adapter: ClaudeCodeAdapter, which spawns the `claude` CLI as a subprocess.

## Depends On
- Chunk 05 (Adapter Interface)
- Chunk 15 (Run Event System — emits execution events via `ctx.on_event`)

## Referenced By
- Chunk 07 — Celery Setup & Run Execution (first adapter to test with)

## Deliverables

### 1. Adapter Implementation — `agents/claude_code.py`

```python
class ClaudeCodeAdapter(BaseAdapter):

    adapter_type: ClassVar[str] = "claude_code"

    @classmethod
    def get_default_config(cls) -> ClaudeCodeConfig:
        """Return a ClaudeCodeConfig with all defaults."""
        return ClaudeCodeConfig()

    @classmethod
    def validate_config(cls, raw_config: dict) -> ClaudeCodeConfig:
        """Validate and coerce raw adapter_config dict into ClaudeCodeConfig."""
        return ClaudeCodeConfig.model_validate(raw_config)

    async def health_check(self) -> bool:
        """Check if `claude` CLI is installed and accessible."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=PIPE, stderr=PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    async def execute(self, ctx: RunContext) -> RunResult:
        start = time.monotonic()

        # 1. Read agent identity files
        soul = read_file(Path(ctx.agent_dir) / "SOUL.md")
        agents_md = read_file(Path(ctx.agent_dir) / "AGENTS.md")

        # 2. Build the message
        if ctx.heartbeat:
            heartbeat_md = read_file(Path(ctx.agent_dir) / "HEARTBEAT.md")
            message = f"Heartbeat check. Review your checklist:\n{heartbeat_md}"
        else:
            message = ctx.message

        # 3. Build environment variables
        env = {
            **os.environ,
            "GATEWAY_URL": ctx.gateway_url,
            "GATEWAY_AGENT_TOKEN": ctx.agent_token,
            "GATEWAY_AGENT_ID": ctx.agent_id,
            "GATEWAY_AGENT_SLUG": ctx.agent_slug,
            "GATEWAY_ORG_SLUG": ctx.org_slug,
            "GATEWAY_RUN_ID": ctx.run_id,
            **ctx.env_vars,
        }

        # 4. Build CLI args from adapter_config + tools from RunContext
        args = self._build_cli_args(ctx, message, soul, ctx.tools)

        # 5. Spawn claude CLI
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.agent_dir,
            env=env,
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()

        duration = time.monotonic() - start

        # 6. Parse token usage from stderr/output
        token_usage = self._parse_usage(stderr.decode())

        return RunResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            token_usage=token_usage,
            duration_seconds=duration,
            error=stderr.decode() if proc.returncode != 0 else None,
        )
```

### 2. CLI Args Builder

`adapter_config` in `RunContext` is already merged (defaults + overrides) and validated as a `ClaudeCodeConfig` dict. Tool permissions come from `RunContext.tools` (populated from `gateway.json` by the context builder), not from adapter config.

```python
def _build_cli_args(
    self, ctx: RunContext, message: str, system_prompt: str,
    tools: list[str] | None = None,
) -> list[str]:
    cfg = ClaudeCodeConfig.model_validate(ctx.adapter_config)
    args = ["claude"]

    # Non-interactive mode
    args.extend(["--print"])

    # Message
    args.extend(["--prompt", message])

    # System prompt (SOUL.md content)
    args.extend(["--system-prompt", system_prompt])

    # Model override
    if cfg.model:
        args.extend(["--model", cfg.model])

    # Max tokens
    if cfg.max_tokens:
        args.extend(["--max-tokens", str(cfg.max_tokens)])

    # Max turns
    if cfg.max_turns:
        args.extend(["--max-turns", str(cfg.max_turns)])

    # Tool permissions from RunContext (sourced from gateway.json)
    if tools is not None:
        # Explicit tool list: auto-approve these, deny everything else
        for tool in tools:
            args.extend(["--allowedTools", tool])
    else:
        # No tool restrictions: skip all permission prompts
        args.append("--dangerously-skip-permissions")

    # Output format
    args.extend(["--output-format", "json"])

    return args
```

### 3. Token Usage Parser

Parse Claude CLI output/stderr for token usage information:

```python
def _parse_usage(self, stderr: str) -> dict | None:
    # Parse JSON output format for usage stats
    # Return: {"input_tokens": N, "output_tokens": N, "cost_usd": N}
    # Return None if parsing fails
    ...
```

### 4. Register in Lifespan

Update `api/lifespan.py`:
```python
adapter_registry.register(ClaudeCodeAdapter())
```

### 5. Adapter Config Schema

Typed by `ClaudeCodeConfig` (defined in `models/adapter.py`). All fields are optional with `None` defaults — missing fields mean "use CLI default".

| Field           | Type             | Default | Description                          |
|-----------------|------------------|---------|--------------------------------------|
| `model`         | `str \| None`    | `None`  | Model override (e.g. `claude-sonnet-4-6`) |
| `max_tokens`    | `int \| None`    | `None`  | Max output tokens                    |
| `max_turns`     | `int \| None`    | `None`  | Max agentic turns                    |

**Note:** Tool permissions are NOT part of adapter config. They live in `gateway.json.tools` and are agent-level, not adapter-level. This allows any adapter type to enforce the same tool list.

Example stored `adapter_config` (only overrides, not full defaults):

```json
{
  "model": "claude-sonnet-4-6",
  "max_turns": 10
}
```

## Notes
- The adapter reads SOUL.md and AGENTS.md from disk — these are the agent's identity.
- Tool permissions come from `RunContext.tools` (populated by the context builder from `gateway.json`). The adapter does not read gateway.json directly.
- When `tools` is a list: `--allowedTools` auto-approves those tools and denies everything else. Unapproved tool use fails the turn.
- When `tools` is `None` (no restrictions): `--dangerously-skip-permissions` is passed to allow all tools without prompts.
- For heartbeat runs, HEARTBEAT.md is used as the prompt.
- Gateway env vars are injected so the agent can discover the gateway at runtime.
- `--print` flag ensures non-interactive execution.
- Token usage parsing depends on Claude CLI output format — may need adjustment.
- `adapter_type = "claude_code"` class variable drives `name()` via `BaseAdapter`.
- `validate_config()` raises `pydantic.ValidationError` on unknown or invalid fields; callers surface as HTTP 422.
- Future: support `--resume` for session persistence across heartbeats (Open Question #1).

## Change Log

| Date       | Change                                                                                          |
|------------|-------------------------------------------------------------------------------------------------|
| 2026-04-06 | Added `adapter_type: ClassVar[str] = "claude_code"` class variable                             |
| 2026-04-06 | Added `get_default_config()` classmethod returning `ClaudeCodeConfig()`                        |
| 2026-04-06 | Added `validate_config()` classmethod returning `ClaudeCodeConfig.model_validate(raw_config)`  |
| 2026-04-06 | Updated CLI args builder to use typed `ClaudeCodeConfig` (added `max_turns`, `allowed_tools`)  |
| 2026-04-06 | Replaced JSON schema block with typed `ClaudeCodeConfig` field table referencing `models/adapter.py` |
| 2026-04-08 | Tool permissions moved from `ClaudeCodeConfig.allowed_tools` to `gateway.json.tools`; adapter reads gateway.json at runtime |
| 2026-04-08 | Added `--dangerously-skip-permissions` flag for headless execution; removed `allowed_tools` from adapter config |
