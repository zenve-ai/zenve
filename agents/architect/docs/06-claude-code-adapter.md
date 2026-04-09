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

        # 2. Build system prompt: runtime identity + persona + behavioral instructions
        identity = (
            f"# Your Identity\n"
            f"- agent_id: {ctx.agent_id}\n"
            f"- agent_slug: {ctx.agent_slug}\n"
            f"- agent_name: {ctx.agent_name}\n"
            f"- org_id: {ctx.org_id}\n"
            f"- org_slug: {ctx.org_slug}\n"
            f"- run_id: {ctx.run_id}\n"
            f"- gateway_url: {ctx.gateway_url}\n"
        )
        system_prompt = f"{identity}\n\n{soul}\n\n{agents_md}"

        # 3. Build the user message (task only — no instructions)
        if ctx.heartbeat:
            heartbeat_md = read_file(Path(ctx.agent_dir) / "HEARTBEAT.md")
            message = f"Heartbeat tick. Review your checklist:\n\n{heartbeat_md}"
        else:
            message = ctx.message or "(no message provided)"

        # 4. Build environment variables
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

        # 5. Build CLI args and spawn claude CLI
        args = self._build_cli_args(config, message, system_prompt, ctx.tools)

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.agent_dir,
            env=env,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

        # 6. Write message to stdin (non-interactive mode)
        proc.stdin.write(message.encode())
        await proc.stdin.drain()
        proc.stdin.close()

        # 7. Stream stdout line-by-line (JSON events from --output-format stream-json)
        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace").strip()
            if not line:
                continue
            # parse and emit events via ctx.on_event(type, text, metadata)
            ...

        await proc.wait()
        duration = time.monotonic() - start

        return RunResult(
            exit_code=proc.returncode or 0,
            stdout=...,
            stderr=...,
            token_usage=token_usage,
            duration_seconds=duration,
            error=stderr if proc.returncode != 0 else None,
        )
```

### 2. CLI Args Builder

`adapter_config` in `RunContext` is already merged (defaults + overrides) and validated as a `ClaudeCodeConfig` dict. Tool permissions come from `RunContext.tools` (populated from `gateway.json` by the context builder), not from adapter config.

```python
def _build_cli_args(
    self,
    config: ClaudeCodeConfig,
    message: str,
    system_prompt: str,
    tools: list[str] | None = None,
) -> list[str]:
    args = [
        "claude",
        "--print",
        "--verbose",
        "--output-format", config.output_format,   # "stream-json"
    ]

    # System prompt: identity + SOUL.md + AGENTS.md
    args.extend(["--system-prompt", system_prompt])

    # Model override
    if config.model:
        args.extend(["--model", config.model])

    # Max tokens
    if config.max_tokens:
        args.extend(["--max-tokens", str(config.max_tokens)])

    # Max turns
    if config.max_turns:
        args.extend(["--max-turns", str(config.max_turns)])

    # Tool permissions from RunContext (sourced from gateway.json)
    if tools is not None:
        # Explicit tool list: auto-approve these, deny everything else
        args.extend(["--allowedTools", ",".join(tools)])
    else:
        # No tool restrictions: skip all permission prompts
        args.append("--dangerously-skip-permissions")

    # Message is passed via stdin, not --prompt
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
- **System prompt composition** — `--system-prompt` is built from three layers in order: runtime identity block → SOUL.md (persona) → AGENTS.md (behavioral instructions). This keeps the agent's operational context fixed and separate from the task.
- **Message is task-only** — stdin carries only the user's task (or heartbeat content). No AGENTS.md prefix. This gives the model a clean human-turn with no instruction noise mixed in.
- **Identity block** — injected at the top of the system prompt so the agent always knows its own `agent_id`, `agent_slug`, `agent_name`, `org_id`, `org_slug`, `run_id`, and `gateway_url`, even without reading `gateway.json`.
- **AGENTS.md placement rationale** — behavioral instructions (On Start, Executing the Task, On Finish) are part of the agent's permanent operating context, not a task. Placing them in the system prompt (not the message) correctly models this distinction.
- Tool permissions come from `RunContext.tools` (populated by the context builder from `gateway.json`). The adapter does not read `gateway.json` directly.
- When `tools` is a list: `--allowedTools` auto-approves those tools and denies everything else. Unapproved tool use fails the turn.
- When `tools` is `None` (no restrictions): `--dangerously-skip-permissions` is passed to allow all tools without prompts.
- For heartbeat runs, HEARTBEAT.md is used as the message (user turn), not the system prompt.
- Gateway env vars are also injected as environment variables (redundant with identity block, but useful for shell scripts running inside the agent).
- `--print` + `--verbose` + `--output-format stream-json` enables line-by-line JSON event streaming from stdout.
- Message is written to stdin after process spawn, not via `--prompt` CLI flag.
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
| 2026-04-09 | Injected runtime identity block (`agent_id`, `agent_slug`, `agent_name`, `org_id`, `org_slug`, `run_id`, `gateway_url`) as first section of `--system-prompt` |
| 2026-04-09 | Moved AGENTS.md from user message prefix into `--system-prompt` (after SOUL.md); message now carries task only |
| 2026-04-09 | Message delivery changed from `--prompt` CLI flag to stdin write after process spawn |
| 2026-04-09 | Added `--verbose` flag; output format changed to `stream-json` for line-by-line event streaming |
