# Chunk 06 — Concrete Adapters (ClaudeCode & OpenCode)

## Goal
Implement the first two concrete adapters: `ClaudeCodeAdapter` (spawns the `claude` CLI) and `OpenCodeAdapter` (spawns the `opencode` CLI). Both follow the same pattern — subprocess spawn, stdin injection, streaming JSON event parsing, token usage capture — but differ in CLI interface and event format.

## Depends On
- Chunk 05 — Adapter Interface (`BaseAdapter`, `RunContext`, `RunResult`, config models)

## Referenced By
- Chunk 07 — Celery Setup & Run Execution (first adapters to execute with)

---

## Deliverables

### 1. Shared Execution Pattern

Both adapters follow the same steps in `execute()`:

1. Validate and coerce `ctx.adapter_config` into the typed config model.
2. Read agent identity files from disk (`SOUL.md`, `AGENTS.md`, `RUN.md` or `HEARTBEAT.md`).
3. Build a context block (runtime identity key/values) and compose the system prompt.
4. Build env vars (gateway context injected as `GATEWAY_*` env vars).
5. Spawn subprocess with `asyncio.create_subprocess_exec`, `cwd=ctx.agent_dir`.
6. Write message to stdin, close stdin.
7. Stream stdout line-by-line, parse JSON events, call `ctx.on_event()` for each.
8. Wait for process exit, collect stderr.
9. Return `RunResult`.

---

### 2. System Prompt Composition

Both adapters build the system prompt the same way:

**Context block** (always first):
```
# IMPORTANT context:
- agent_id: {ctx.agent_id}
- agent_slug: {ctx.agent_slug}
- agent_name: {ctx.agent_name}
- org_id: {ctx.org_id}
- org_slug: {ctx.org_slug}
- run_id: {ctx.run_id}
- gateway_url: {ctx.gateway_url}
```

**Normal run system prompt:** `context + SOUL.md + AGENTS.md + RUN.md`
**Normal run message (stdin):** `ctx.message or "(no message provided)"`

**Heartbeat system prompt:** `context + SOUL.md + AGENTS.md + HEARTBEAT.md`
**Heartbeat message (stdin):** `"Heartbeat tick."`

HEARTBEAT.md is part of the system prompt, not the user message, so the agent's tick instructions are treated as permanent operational context.

---

### 3. Environment Variables

Both adapters inject:

| Env Var | Value |
|---------|-------|
| `GATEWAY_URL` | `ctx.gateway_url` |
| `GATEWAY_AGENT_TOKEN` | `ctx.agent_token` |
| `GATEWAY_AGENT_ID` | `ctx.agent_id` |
| `GATEWAY_AGENT_SLUG` | `ctx.agent_slug` |
| `GATEWAY_ORG_SLUG` | `ctx.org_slug` |
| `GATEWAY_RUN_ID` | `ctx.run_id` |

Plus any extra `ctx.env_vars` merged in. OpenCode additionally sets:
- `OPENCODE_PERMISSION='{"*": "allow"}'` — grants all tool permissions
- `OPENCODE_DISABLE_PROJECT_CONFIG=true` — prevents opencode from reading project config

---

### 4. ClaudeCodeAdapter — `adapters/claude_code.py`

`adapter_type = "claude_code"` · spawns `claude` CLI

**CLI args built by `build_cli_args()`:**
```
claude --print --verbose --output-format stream-json
       --system-prompt <composed system prompt>
       [--model <model>]
       [--max-tokens <n>]
       [--max-turns <n>]
       [--allowedTools <tool1,tool2>]   # if ctx.tools is not None
       [--dangerously-skip-permissions] # if ctx.tools is None
```

Message is written to stdin (not via `--prompt` flag).

**Stream-JSON event types parsed:**

| Event type | Action |
|------------|--------|
| `system` | Emit `("output", "Session started: {id}", {"session_id": ...})` |
| `assistant` + text block | Emit `("output", text, None)` |
| `assistant` + tool_use block | Emit `("tool_call", "Calling tool: {name}", {"tool", "tool_use_id", "input"})` |
| `user` + tool_result block | Emit `("tool_result", summary[:500], {"tool_use_id", "is_error", "full_result"})` |
| `result` | Emit `("usage", None, {input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens, cost_usd})` |
| `error` | Emit `("error", message, {"type": "error"})` |

**Config — `ClaudeCodeConfig`:**

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `"claude-sonnet-4-6"` | Model override |
| `max_tokens` | `None` | Max output tokens |
| `max_turns` | `10` | Max agentic turns |
| `output_format` | `"stream-json"` | CLI output format |

**Health check:** `claude --version` → returncode 0.

---

### 5. OpenCodeAdapter — `adapters/open_code.py`

`adapter_type = "open_code"` · spawns `opencode` CLI

**CLI args:**
```
opencode run --format json [--model <model>]
```

**Stdin payload:** `{system_prompt}\n\n---\n\n{message}` — system prompt and message are concatenated and written as a single stdin payload (opencode does not have a `--system-prompt` flag).

**Stream-JSON event types parsed:**

| Event type | Action |
|------------|--------|
| First event with `sessionID` | Emit `("output", "Session started: {id}", {"session_id": ...})` |
| `text` | Emit `("output", part.text, None)` |
| `tool_use` | Emit `("tool_call", "Calling tool: {name}", {"tool", "input", ["error"]})` |
| `step_finish` | Emit `("usage", None, {input_tokens, output_tokens, reasoning_tokens, cache_read_input_tokens, cost_usd})` |
| `error` | Emit `("error", message, {"type": "error"})` |

**Config — `OpenCodeConfig`:**

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `""` | Model override (empty = CLI default) |
| `max_tokens` | `None` | Max output tokens |
| `steps` | `10` | Max steps |
| `output_format` | `"json"` | CLI output format |

**Health check:** `opencode --version` → returncode 0.

---

### 6. `read_file()` Helper

Both adapters share the same static helper:

```python
@staticmethod
def read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"(file not found: {path.name})"
```

Missing files return a descriptive placeholder rather than raising — the agent can still run and will see the missing-file note in its context.

---

### 7. Register in Lifespan

```python
# api/lifespan.py
adapter_registry.register(ClaudeCodeAdapter())
adapter_registry.register(OpenCodeAdapter())
```

---

## Notes

- Tool permissions for `claude_code`: `--allowedTools` auto-approves listed tools and denies others. `--dangerously-skip-permissions` (when `tools=None`) allows everything without prompts — required for headless execution.
- Tool permissions for `open_code`: controlled via `OPENCODE_PERMISSION='{"*": "allow"}'` env var — there is no per-tool CLI flag, so the env var grants all tools and per-agent restrictions are advisory only.
- Token usage fields differ between adapters: Claude Code includes `cache_creation_input_tokens`; OpenCode includes `reasoning_tokens` instead.
- Both adapters have a `parse_token_usage()` method but the primary token extraction is inline during stream parsing.
- Non-zero `proc.returncode` sets `RunResult.error = stderr`; adapters never raise on non-zero exit.

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-06 | Created chunk: ClaudeCodeAdapter implementation, CLI args builder, token usage parser | First concrete adapter |
| 2026-04-08 | Tool permissions moved to RunContext.tools; `--dangerously-skip-permissions` added for headless runs | Agent-level tool control |
| 2026-04-09 | Runtime identity context block injected at top of `--system-prompt`; AGENTS.md moved to system prompt; message is task-only via stdin | Cleaner prompt structure |
| 2026-04-09 | Output format changed to `stream-json`; `--verbose` added; message via stdin not `--prompt` | Line-by-line event streaming |
| 2026-04-10 | Added OpenCodeAdapter (`open_code`); documented shared execution pattern; RUN.md added to system prompt for normal runs; HEARTBEAT.md in system prompt (not message); context block header changed to `# IMPORTANT context:`; full event parsing tables; token usage field details | Reflects implemented adapters package |
