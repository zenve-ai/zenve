# Chunk 06 — Claude Code Adapter

## Goal
Implement the first concrete adapter: ClaudeCodeAdapter, which spawns the `claude` CLI as a subprocess.

## Depends On
- Chunk 05 (Adapter Interface)

## Deliverables

### 1. Adapter Implementation — `agents/claude_code.py`

```python
class ClaudeCodeAdapter(BaseAdapter):

    def name(self) -> str:
        return "claude_code"

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

        # 4. Build CLI args from adapter_config
        args = self._build_cli_args(ctx, message, soul)

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

```python
def _build_cli_args(self, ctx: RunContext, message: str, system_prompt: str) -> list[str]:
    args = ["claude"]

    # Non-interactive mode
    args.extend(["--print"])   # or appropriate flag for non-interactive

    # Message
    args.extend(["--prompt", message])

    # System prompt (SOUL.md content)
    args.extend(["--system-prompt", system_prompt])

    # Model override from adapter_config
    if model := ctx.adapter_config.get("model"):
        args.extend(["--model", model])

    # Max tokens from adapter_config
    if max_tokens := ctx.adapter_config.get("max_tokens"):
        args.extend(["--max-tokens", str(max_tokens)])

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

Document expected `adapter_config` fields for Claude Code:

```json
{
  "model": "claude-sonnet-4-6",         // optional, default: CLI default
  "max_tokens": 4096,                    // optional
  "allowed_tools": ["Read", "Write"],    // optional, restrict tools
  "max_turns": 10                        // optional
}
```

## Notes
- The adapter reads SOUL.md and AGENTS.md from disk — these are the agent's identity.
- For heartbeat runs, HEARTBEAT.md is used as the prompt.
- Gateway env vars are injected so the agent can discover the gateway at runtime.
- `--print` flag (or equivalent) ensures non-interactive execution.
- Token usage parsing depends on Claude CLI output format — may need adjustment.
- Future: support `--resume` for session persistence across heartbeats (Open Question #1).
